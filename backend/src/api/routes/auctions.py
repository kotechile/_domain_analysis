"""
Auctions API routes for multi-source domain auction data
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Body, BackgroundTasks, Depends
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import structlog
import uuid
import asyncio

from services.auctions_service import AuctionsService
from services.database import get_database
from services.n8n_service import N8NService
from services.auction_scoring_service import AuctionScoringService
from services.domain_scoring_service import DomainScoringService
from services.external_apis import WaybackMachineService, DataForSEOService
from services.credits_service import CreditsService
from services.pricing_service import PricingService
from middleware.auth_middleware import get_current_user
from models.auctions import AuctionReportItem
from models.domain_analysis import NamecheapDomain
from utils.date_utils import parse_iso_datetime

logger = structlog.get_logger()
router = APIRouter()

# Global lock to prevent multiple concurrent uploads from saturating CPU/DB
_upload_status_lock = asyncio.Lock()

# Number of parallel staging tables for concurrent inserts
NUM_STAGING_TABLES = 5


def get_staging_table_index(domain: str) -> int:
    """
    Get staging table index (0-4) for a given domain using hash-based partitioning.
    Same domain always maps to same table for idempotent inserts.
    """
    return abs(hash(domain)) % NUM_STAGING_TABLES


def get_staging_table_name(index: int) -> str:
    """Get staging table name for given index."""
    return f"auctions_staging_{index}"


async def _clear_staging_table_chunked(db, staging_index: int, job_id: str):
    """
    Clear a specific staging table (by index) in chunks to avoid statement timeouts.
    """
    table_name = get_staging_table_name(staging_index)
    logger.info(f"Clearing staging table {table_name} in chunks", job_id=job_id, staging_index=staging_index)
    total_cleared = 0

    while True:
        client = await db._get_client()
        clear_res = await client.table(table_name).select('domain').eq('job_id', job_id).limit(5000).execute()
        if not clear_res.data:
            break

        domains_to_del = [r['domain'] for r in clear_res.data]
        for j in range(0, len(domains_to_del), 100):
            sub_domains = domains_to_del[j:j + 100]
            await client.table(table_name).delete().eq('job_id', job_id).in_('domain', sub_domains).execute()

        total_cleared += len(domains_to_del)
        await asyncio.sleep(0.01)

    logger.info(f"Staging table {table_name} cleared", job_id=job_id, staging_index=staging_index, total=total_cleared)
    return total_cleared


async def _clear_all_staging_tables_chunked(db, job_id: str):
    """
    Clear all 5 staging tables for a given job_id.
    Used for cleanup on failure.
    """
    logger.info("Clearing all staging tables", job_id=job_id)
    tasks = [_clear_staging_table_chunked(db, i, job_id) for i in range(NUM_STAGING_TABLES)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    total = sum(r for r in results if isinstance(r, int))
    failed = [i for i, r in enumerate(results) if isinstance(r, Exception)]

    if failed:
        logger.warning("Some staging tables failed to clear", job_id=job_id, failed_tables=failed)

    return total


async def _perform_rpc_merge(db, auction_site: str, job_id: str, staging_suffix: int, offering_type: str = None) -> int:
    """
    Merge from a specific staging table using the SQL delta merge RPC function.
    Returns number of new domains inserted (for scoring tracking).
    """
    logger.info(f"Starting RPC merge for staging table {staging_suffix}", job_id=job_id, site=auction_site)

    client = await db._get_client()

    try:
        result = await client.rpc('merge_auctions_delta_from_staging', {
            'p_auction_site': auction_site,
            'p_job_id': job_id,
            'p_offering_type': offering_type,
            'p_staging_table_suffix': staging_suffix
        }).execute()

        if result.data:
            new_domains = [r for r in result.data if r.get('is_new')]
            logger.info(f"RPC merge complete", job_id=job_id, staging_table=staging_suffix, new_domains=len(new_domains))
            return len(new_domains)

        return 0

    except Exception as e:
        logger.error(f"RPC merge failed for staging table {staging_suffix}", job_id=job_id, error=str(e))
        raise


@router.get("/auctions/troubleshoot-uploads")
async def troubleshoot_uploads( limit: int = 10 ):
    """
    Combined troubleshooting endpoint for debugging upload and processing issues. Lists recent jobs, staging counts, and storage state. """
    try:
        db = get_database()
        client = await db._get_client()
        
        # 1. Recent jobs
        jobs_res = await client.table('csv_upload_progress').select('*').order('updated_at', desc=True).limit(limit).execute()
        
        # 2. Staging count
        staging_count_res = await client.table('auctions_staging').select('count', count='exact').limit(1).execute()
        
        # 3. Storage buckets (to verify permissions/connection)
        try:
             storage_res = client.storage.list_buckets()
             buckets = [b.name for b in storage_res] if storage_res else []
        except:
             buckets = "Error or unauthorized to list buckets"
             
        return { 
            "success": True, 
            "recent_jobs": jobs_res.data if jobs_res else [], 
            "staging_total_exact": staging_count_res.count if staging_count_res else 0,
            "storage_buckets": buckets 
        }
    except Exception as e:
        logger.error("Troubleshooting failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug-storage-list")
async def debug_list_storage( bucket: str = "auction-csvs", prefix: str = "" ):
    """
    Debug endpoint to list files in a bucket to verify exact paths. Use this when you get 404/400 errors despite the file appearing to exist. """
    try:
        db = get_database()
        client = await db._get_client()
        
        # List files in bucket
        res = client.storage.from_(bucket).list(prefix)
        
        return { "success": True, "bucket": bucket, "prefix": prefix, "files_count": len(res) if res else 0, "files": res }
    except Exception as e:
        logger.error("Failed to list storage files", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def _clear_staging_chunked(db, auction_site: str, job_id: str):
    """
    Clear staging table for a specific site in chunks to avoid statement timeouts. """
    logger.info("Clearing staging table in chunks", job_id=job_id, site=auction_site)
    total_cleared = 0
    while True:
        # Fetch domains for this job
        clear_res = await (await db._get_client()).table('auctions_staging').select('domain').eq('job_id', job_id).limit(5000).execute()
        if not clear_res.data:
            break
        
        domains_to_del = [r['domain'] for r in clear_res.data]
        # Use small sub-batches for IN filter to avoid URL length limit
        for j in range(0, len(domains_to_del), 100):
            sub_domains = domains_to_del[j:j + 100]
            await (await db._get_client()).table('auctions_staging').delete().eq('job_id', job_id).in_('domain', sub_domains).execute()
        
        total_cleared += len(domains_to_del)
        await asyncio.sleep(0.01)
    
    logger.info("Staging table cleared successfully", job_id=job_id, site=auction_site, total=total_cleared)
    return total_cleared


async def _mark_auctions_for_deletion(db, auction_site: str, offering_type: str = None):
    """
    Mark all auctions for a site with to_delete=true at start of import. Records that are still present in new files will be unflagged during merge. """
    logger.info("Marking auctions for deletion", auction_site=auction_site, offering_type=offering_type)
    try:
        # Update all records for this auction_site to set to_delete = true
        # We do this in chunks to avoid timeouts
        while True:
            query = (await db._get_client()).table('auctions').select('domain').eq('auction_site', auction_site).eq('to_delete', False)
            if offering_type:
                query = query.eq('offer_type', offering_type)
            result = await query.limit(5000).execute()

            if not result.data:
                break

            domains = [r['domain'] for r in result.data]

            # Update in smaller batches
            for i in range(0, len(domains), 100):
                batch = domains[i:i+100]
                update_query = (await db._get_client()).table('auctions').update({'to_delete': True}).eq('auction_site', auction_site)
                if offering_type:
                    update_query = update_query.eq('offer_type', offering_type)
                await update_query.in_('domain', batch).execute()

            await asyncio.sleep(0.01)

        logger.info("Marked auctions for deletion", auction_site=auction_site, offering_type=offering_type)
    except Exception as e:
        logger.error("Failed to mark auctions for deletion", auction_site=auction_site, error=str(e))
        raise


async def _delete_flagged_auctions(db, auction_site: str, offering_type: str = None):
    """
    Delete auctions that still have to_delete=true after merge. These are records that were not present in the new file upload. """
    logger.info("Deleting flagged auctions", auction_site=auction_site, offering_type=offering_type)
    total_deleted = 0

    try:
        # Delete in chunks to avoid timeouts
        while True:
            # Get batch of records to delete
            query = (await db._get_client()).table('auctions').select('domain').eq('auction_site', auction_site).eq('to_delete', True)
            if offering_type:
                query = query.eq('offer_type', offering_type)
            result = await query.limit(1000).execute()

            if not result.data:
                break

            domains = [r['domain'] for r in result.data]

            # Delete in smaller batches
            for i in range(0, len(domains), 100):
                batch = domains[i:i+100]
                del_query = (await db._get_client()).table('auctions').delete().eq('auction_site', auction_site).eq('to_delete', True)
                if offering_type:
                    del_query = del_query.eq('offer_type', offering_type)
                await del_query.in_('domain', batch).execute()
                total_deleted += len(batch)

            await asyncio.sleep(0.01)

        logger.info("Deleted flagged auctions", auction_site=auction_site, offering_type=offering_type, total_deleted=total_deleted)
        return total_deleted
    except Exception as e:
        logger.error("Failed to delete flagged auctions", auction_site=auction_site, error=str(e))
        raise


async def _perform_python_chunked_merge(db, auction_site: str, job_id: str, offering_type: str = None):
    """
    Perform merging from staging to main table in chunks from Python
    to avoid database statement timeouts. """
    logger.info("Starting chunked merge from Python", job_id=job_id, site=auction_site, offering_type=offering_type)

    total_merged = 0

    while True:
        # 1. Fetch a batch of records from staging
        # We also need to fetch columns that we want to keep if they are in the staging record, # but the staging record usually only has basic auction info.
        # Fetch a smaller batch to prevent large HTTP upsert bodies triggering SSL drops
        result = await (await db._get_client()).table('auctions_staging').select('*').eq('job_id', job_id).limit(500).execute()
        records = result.data

        if not records:
            break

        # 2. Prepare for upsert to main table
        # ON CONFLICT DO UPDATE command cannot affect row a second time" error.
        unique_records = {}

        # Pre-fetch existing domains to preserve their scores and source_data
        existing_domains = set()
        for r in records:
            key = (r.get('domain'), r.get('auction_site'), r.get('expiration_date'))
            existing_domains.add(key)

        # Fetch existing scores and source_data in batch
        existing_data = {}
        if existing_domains:
            # Build query for existing domains
            client = await db._get_client()
            for key in existing_domains:
                domain, auction_site, exp_date = key
                try:
                    existing_result = await client.table('auctions').select('domain', 'score', 'source_data').eq('domain', domain).eq('auction_site', auction_site).eq('expiration_date', exp_date).limit(1).execute()
                    if existing_result.data:
                        existing_data[key] = {
                            'score': existing_result.data[0].get('score'),
                            'source_data': existing_result.data[0].get('source_data')
                        }
                except Exception:
                    pass

        for r in records:
            # Key must match the database unique constraint: domain + auction_site + expiration_date
            key = (r.get('domain'), r.get('auction_site'), r.get('expiration_date'))

            # Extract link from source_data if not present
            link = r.get('link')
            source_data = r.get('source_data') or {}
            if not link and isinstance(source_data, dict):
                link = source_data.get('link')

            # Preserve existing score and source_data for updates (new records have None)
            preserved = existing_data.get(key, {})
            existing_score = preserved.get('score')
            existing_source = preserved.get('source_data')

            # For new records: score is None (will be scored later), source_data is from file
            # For existing records: keep their score and source_data
            clean_r = { 'domain': r.get('domain'), 'start_date': r.get('start_date'), 'expiration_date': r.get('expiration_date'), 'auction_site': r.get('auction_site'), 'current_bid': r.get('current_bid'), 'link': link, 'offer_type': r.get('offer_type'), 'first_seen': r.get('first_seen'), 'to_delete': False }

            # Only include score if it's not None (new records have None, existing keep their score)
            if r.get('score') is not None:
                clean_r['score'] = r.get('score')
            elif existing_score is not None:
                clean_r['score'] = existing_score

            # Only include source_data if it has meaningful data
            if r.get('source_data') is not None:
                clean_r['source_data'] = r.get('source_data')
            elif existing_source is not None:
                clean_r['source_data'] = existing_source

            unique_records[key] = clean_r

        main_records = list(unique_records.values())

        # 3. Upsert to main table with retries for network stability
        try:
            client = await db._get_client()
            retries = 3
            for attempt in range(retries):
                try:
                    await client.table('auctions').upsert( main_records, on_conflict='domain,auction_site,expiration_date' ).execute()
                    break
                except Exception as e:
                    if attempt == retries - 1:
                        raise
                    logger.warning("SSL or network error during chunked upsert, retrying", attempt=attempt, error=str(e))
                    await asyncio.sleep(2 ** attempt)

            # 4. Delete merged records from staging in small sub-batches
            # ) Use smaller batches for the IN filter to avoid "URL component 'query' too long" (max ~2000 chars
            domains = [r['domain'] for r in records]
            sub_batch_size = 100 # Safe size for URLs
            for j in range(0, len(domains), sub_batch_size):
                sub_domains = domains[j:j + sub_batch_size]
                await (await db._get_client()).table('auctions_staging').delete().eq('job_id', job_id).in_('domain', sub_domains).execute()

            total_merged += len(records)
            logger.info("Merged batch successfully", job_id=job_id, site=auction_site, count=len(records), total=total_merged)

            # Update progress
            await db.update_csv_upload_progress( job_id=job_id, current_stage='merging', inserted_count=total_merged )

        except Exception as e:
            logger.error("Failed to merge batch in Python", job_id=job_id, site=auction_site, error=str(e))
            raise

        await asyncio.sleep(0.1)

    # Post-merge: Delete auctions that still have to_delete=true
    # These are records that were not present in the new file upload
    try:
        deleted_count = await _delete_flagged_auctions(db, auction_site, offering_type)
        logger.info("Post-merge cleanup completed", job_id=job_id, site=auction_site, offering_type=offering_type, deleted_count=deleted_count)
    except Exception as e:
        logger.warning("Failed to delete flagged auctions after merge", job_id=job_id, site=auction_site, error=str(e))

    return total_merged


async def _score_new_domains_after_merge(db, auction_site: str, scoring_service, job_id: str, fast_mode: bool = False) -> int:
    """
    Score only NEW domains that were just inserted (score is NULL).
    Existing domains kept their previous score.

    OPTIMIZED: Uses batch SELECT and batch UPDATE to minimize SSL connections.
    """
    logger.info("Starting post-merge scoring for new domains", job_id=job_id, auction_site=auction_site, fast_mode=fast_mode)

    total_scored = 0
    BATCH_SIZE = 200  # Fetch and score in batches
    MAX_UPDATE_BATCH = 50  # Smaller batches for DB updates to avoid SSL issues

    while True:
        # Fetch unprocessed/new domains (score is NULL)
        result = await (await db._get_client()).table('auctions').select(
            'domain', 'expiration_date', 'start_date'
        ).eq('auction_site', auction_site).is_('score', None).limit(BATCH_SIZE).execute()

        if not result.data:
            break

        domains_to_score = result.data
        logger.info("Found domains needing scoring", job_id=job_id, count=len(domains_to_score), total_scored=total_scored)

        # Score all domains in the batch first
        scored_domains = []
        for record in domains_to_score:
            try:
                domain_name = record['domain']

                # Create NamecheapDomain for scoring
                namecheap_domain = NamecheapDomain(
                    name=domain_name,
                    registered_date=None,
                    url=None,
                    start_date=record.get('start_date'),
                    end_date=record.get('expiration_date'),
                    price=None
                )

                # Score the domain
                scored = scoring_service.score_domain(namecheap_domain, fast_mode=fast_mode)
                score_value = scored.total_meaning_score if scored.total_meaning_score is not None else None

                scored_domains.append({
                    'domain': domain_name,
                    'score': score_value,
                    'expiration_date': record.get('expiration_date')
                })

            except Exception as e:
                logger.warning("Failed to score domain during post-merge", domain=record.get('domain'), error=str(e))
                # Still include with None score so we don't get stuck
                scored_domains.append({
                    'domain': record.get('domain'),
                    'score': None,
                    'expiration_date': record.get('expiration_date')
                })

        # Batch update - use smaller sub-batches to avoid SSL issues
        for i in range(0, len(scored_domains), MAX_UPDATE_BATCH):
            sub_batch = scored_domains[i:i + MAX_UPDATE_BATCH]
            try:
                # Update each domain individually but in small batches
                for sd in sub_batch:
                    await (await db._get_client()).table('auctions').update({
                        'score': sd['score'],
                        'processed': True
                    }).eq('domain', sd['domain']).eq('auction_site', auction_site).eq('expiration_date', sd['expiration_date']).execute()
                    total_scored += 1
            except Exception as e:
                logger.warning("Batch update failed, falling back to individual updates", error=str(e))
                # Fallback to individual updates
                for sd in sub_batch:
                    try:
                        await (await db._get_client()).table('auctions').update({
                            'score': sd['score'],
                            'processed': True
                        }).eq('domain', sd['domain']).eq('auction_site', auction_site).eq('expiration_date', sd['expiration_date']).execute()
                        total_scored += 1
                    except Exception:
                        pass

            # Small delay between batches to let SSL settle
            await asyncio.sleep(0.5)

        # Update progress periodically
        try:
            await db.update_csv_upload_progress(
                job_id=job_id,
                status='processing',
                current_stage='scoring_new',
                processed_records=total_scored
            )
        except Exception:
            pass

    logger.info("Post-merge scoring complete", job_id=job_id, auction_site=auction_site, total_scored=total_scored)
    return total_scored


async def process_csv_upload_async( job_id: str, csv_content: str, filename: str, auction_site: str, offering_type: Optional[str] = None, is_file: bool = False ):
    """
    Background task to process CSV upload with progress tracking using streaming

    Args:
        job_id: Unique job identifier
        csv_content: CSV file content as string OR file path if is_file=True
        filename: Original filename
        auction_site: Auction site source
        is_file: Whether csv_content is a file path
    """
    # Optional memory tracking (psutil may not be installed)
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        start_mem = process.memory_info().rss / 1024 / 1024  # MB
        logger.info(f"[CSV UPLOAD START] {job_id}", filename=filename, auction_site=auction_site, start_memory_mb=start_mem, offering_type=offering_type)
    except ImportError:
        logger.info(f"[CSV UPLOAD START] {job_id}", filename=filename, auction_site=auction_site, offering_type=offering_type)
        start_mem = None

    db = get_database()
    auctions_service = AuctionsService()

    try:
        # Check if another upload is running and mark as queued if so
        if _upload_status_lock.locked():
            logger.info("Another upload is in progress, queuing job", job_id=job_id)
            try:
                await db.update_csv_upload_progress(job_id=job_id, status='queued', current_stage='waiting_for_lock')
            except Exception as e:
                logger.error(f"[CSV UPLOAD] Failed to update queued status: {e}", job_id=job_id)

        async with _upload_status_lock:
            # 1. Count Total Lines (approx) for progress tracking
            # This is creating an extra pass but on local FS it's fast (O(n) sequential read)
            total_records = 0
            if is_file:
                try:
                    # Use bytes mode for fast reading, assuming standard line endings
                    with open(csv_content, 'rb') as f:
                        # Subtract 1 for header, but ensure non-negative
                        count = sum(1 for _ in f) - 1
                        total_records = max(0, count)
                    logger.info("Counted logical lines in file", job_id=job_id, count=total_records, filename=filename)
                except Exception as e:
                    logger.warning("Failed to count lines in file, progress will be approximate", job_id=job_id, error=str(e))
                    total_records = 0
            
            # Update status to parsing
            await db.update_csv_upload_progress( job_id=job_id, status='parsing', current_stage='parsing', total_records=total_records if total_records > 0 else None )
        
            # 2. Clear ALL 5 staging tables for this Job ID to ensure clean slate
            try:
                await _clear_all_staging_tables_chunked(db, job_id)
            except Exception as e:
                logger.warning("Failed to clear staging tables (might be empty), continuing", job_id=job_id, error=str(e))

            # 2.5 Mark all existing auctions for this site with to_delete=true
            # Records still present in new files will be unflagged during merge
            try:
                # For GoDaddy and NameSilo, the files often contain mixed types (Buy Now and Auction).
                # To ensure proper cleanup of stale records, we mark ALL records for these sites.
                # For Namecheap, files are usually separated by type, so we follow the offering_type.
                cleanup_type = offering_type
                if auction_site.lower() in ['godaddy', 'namesilo']:
                    cleanup_type = None
                    
                await _mark_auctions_for_deletion(db, auction_site, cleanup_type)
            except Exception as e:
                logger.warning("Failed to mark auctions for deletion, continuing", job_id=job_id, error=str(e))

            # 3. Stream & Process
            # Helper function to map NameSilo Type field to offer_type
            def map_namesilo_type_to_offer_type(type_field: str) -> str:
                if not type_field:
                    return 'auction'
                type_lower = type_field.lower().strip()
                # Explicit mappings for NameSilo Type field values
                if 'offer/counter' in type_lower or 'offer' in type_lower or 'counter' in type_lower:
                    # Offer/Counter Offer is treated as buy_now
                    return 'buy_now'
                elif type_lower == 'auction':
                    return 'auction'
                elif type_lower == 'expired':
                    # Expired domains are classified as backorder
                    return 'backorder'
                elif 'customer auction' in type_lower:
                    return 'auction'
                elif 'expired domain auction' in type_lower:
                    return 'backorder'
                elif 'backorder' in type_lower:
                    return 'backorder'
                else:
                    return 'auction'

            logger.info("Starting streaming process (FAST MODE - no scoring during upload)", job_id=job_id, auction_site=auction_site)

            # Get generator
            iterator = auctions_service.load_auctions_from_csv(csv_content, auction_site, filename, is_file=is_file)

            # NOTE: We skip scoring during streaming for performance.
            # Scoring will be done AFTER merge for only NEW domains.
            # Existing domains keep their score from previous imports.

            BATCH_SIZE = 1000  # Larger batches since we're just inserting, not scoring
            processed_count = 0
            passed_count = 0
            failed_count = 0
            skipped_count = 0

            # For NameSilo type stats
            namesilo_type_counts = {}
            error_message = None

            # Parallel staging architecture: 5 insert queues, one per staging table
            insert_queues = {i: [] for i in range(NUM_STAGING_TABLES)}
            insert_tasks = []
            insert_errors = []

            async def insert_worker(staging_index: int):
                """Background worker that inserts batches to specific staging table."""
                nonlocal insert_errors
                table_name = get_staging_table_name(staging_index)
                client = await db._get_client()

                while True:
                    await asyncio.sleep(0.01)  # Poll for batches

                    if not insert_queues[staging_index]:
                        continue

                    batch = insert_queues[staging_index]
                    insert_queues[staging_index] = []

                    if not batch:
                        continue

                    try:
                        # Retry logic
                        for attempt in range(3):
                            try:
                                await client.table(table_name).insert(batch).execute()
                                break
                            except Exception as e:
                                if attempt == 2:
                                    insert_errors.append((staging_index, str(e)))
                                    raise
                                await asyncio.sleep(2 ** attempt)
                    except Exception as e:
                        insert_errors.append((staging_index, str(e)))
                        return

            # Start 5 insert workers
            for i in range(NUM_STAGING_TABLES):
                insert_tasks.append(asyncio.create_task(insert_worker(i)))

            async def process_batch_parallel(batch):
                """Partition batch across staging tables and queue for insert."""
                nonlocal processed_count

                if not batch:
                    return

                for record in batch:
                    # Route to appropriate staging table based on domain hash
                    staging_idx = get_staging_table_index(record.get('domain', ''))
                    insert_queues[staging_idx].append(record)

                processed_count += len(batch)

            # Loop through iterator
            total_processed_so_far = 0
            is_namecheap = auction_site.lower() == 'namecheap'
            batch_list = []
            
            for auction_input in iterator:
                total_processed_so_far += 1
                
                # Update progress in DB every 100 records (including skipped/filtered)
                # This makes the dashboard MUCH more responsive for large files
                if total_processed_so_far % 100 == 0:
                    try:
                        await db.update_csv_upload_progress( 
                            job_id=job_id, 
                            status='processing', 
                            processed_records=total_processed_so_far, 
                            current_stage='streaming',
                            total_records=total_records if total_records > 0 else total_processed_so_far + 100 
                        )
                        # Yield control to event loop more frequently
                        await asyncio.sleep(0.005)
                    except Exception:
                        pass
                
                # Periodically log to stdout so Coolify logs show life
                if total_processed_so_far % 5000 == 0:
                    logger.info("Importing records...", job_id=job_id, processed=total_processed_so_far, total_est=total_records)

                try:
                    auction = auction_input.to_auction()
                    
                    # Logic copied from original process_csv_upload_async
                    start_date_iso = auction.start_date.isoformat() if auction.start_date else None
                    expiration_date = auction.expiration_date

                    # Filter: Skip auctions that expire more than 2 weeks in the future
                    if expiration_date and is_namecheap:
                        if expiration_date.tzinfo is None:
                            expiration_date = expiration_date.replace(tzinfo=timezone.utc)
                        two_weeks_from_now = datetime.now(timezone.utc) + timedelta(days=14)
                        if expiration_date > two_weeks_from_now:
                            skipped_count += 1
                            continue
                    elif not expiration_date and is_namecheap:
                        # Namecheap records should have expiration dates - skip if missing
                        logger.debug("Skipping Namecheap record without expiration date", domain=auction.domain)
                        skipped_count += 1
                        continue
                    
                    # NameSilo fallback
                    if not expiration_date and auction_site.lower() == 'namesilo':
                         expiration_date = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
                    
                    expiration_date_iso = expiration_date.isoformat() if expiration_date else None

                    # NOTE: We skip scoring during streaming for performance.
                    # Score will be NULL for all records - we'll score only NEW domains after merge.

                    # Determine offer_type
                    record_offer_type = offering_type
                    if auction_site.lower() == 'namesilo':
                        type_field = auction.source_data.get('Type', '').strip() if auction.source_data else ''
                        record_offer_type = map_namesilo_type_to_offer_type(type_field)
                        namesilo_type_counts[type_field] = namesilo_type_counts.get(type_field, 0) + 1
                    elif auction_site.lower() == 'godaddy':
                        # Extract auctionType from GoDaddy JSON (BuyNow or Bid)
                        auction_type = auction.source_data.get('auctionType', '').strip() if auction.source_data else ''
                        if auction_type.lower() == 'buynow':
                            record_offer_type = 'buy_now'
                        elif auction_type.lower() == 'bid':
                            record_offer_type = 'auction'
                        # If auctionType not found, fall back to offering_type parameter
                        if not record_offer_type:
                            record_offer_type = 'auction'
                    elif auction_site.lower() == 'namecheap':
                        # Detect from filename for Namecheap
                        if 'buy_now' in filename.lower():
                            record_offer_type = 'buy_now'
                        else:
                            record_offer_type = 'auction'
                    elif not record_offer_type:
                         # Detect from filename for Namecheap
                         if 'buy_now' in filename.lower():
                             record_offer_type = 'buy_now'
                         else:
                             record_offer_type = 'auction'

                    # First seen for Namecheap
                    first_seen_date = None
                    if auction_site.lower() == 'namecheap':
                         # Try to get registeredDate from source_data
                         reg_date_str = auction.source_data.get('registeredDate') if auction.source_data else None
                         if reg_date_str:
                             first_seen_date = reg_date_str # Already string or parsed? AuctionInput source_data is dict of strings mostly
                    
                    auction_dict = { 'domain': auction.domain, 'start_date': start_date_iso, 'expiration_date': expiration_date_iso, 'auction_site': auction.auction_site, 'current_bid': auction.current_bid, 'source_data': auction.source_data, 'link': auction.link, 'processed': False, 'preferred': False, 'has_statistics': False, 'score': None, 'ranking': None, 'first_seen': first_seen_date, 'to_delete': False, # Default - processed=False means needs scoring
                        'offer_type': record_offer_type, 'job_id': job_id }
                    
                    batch_list.append(auction_dict)
                    
                    if len(batch_list) >= BATCH_SIZE:
                        await process_batch_parallel(batch_list)
                        batch_list = []
                        # Log progress to stdout for observability
                        logger.info("Processed batch", job_id=job_id, count=processed_count, total_estimated=total_records)

                        
                except Exception as e:
                    logger.warning("Failed to process auction record", domain=getattr(auction_input, 'domain', '?'), error=str(e))
                    skipped_count += 1
                    if not error_message:
                        error_message = f"Record failure ({getattr(auction_input, 'domain', '?')}): {str(e)}"
            
            # Process remaining batch
            if batch_list:
                await process_batch_parallel(batch_list)
                batch_list = []

            # Give workers time to process remaining batches
            await asyncio.sleep(1.0)

            # Cancel workers
            for t in insert_tasks:
                if not t.done():
                    t.cancel()

            # Wait for workers to finish
            await asyncio.gather(*insert_tasks, return_exceptions=True)

            # Check for insert errors
            if insert_errors:
                logger.error("Staging insert failed, cleaning up", job_id=job_id, errors=insert_errors)
                await _clear_all_staging_tables_chunked(db, job_id)
                raise Exception(f"Staging insert failed: {insert_errors}")

            logger.info("Streaming complete (FAST MODE - no scoring)", job_id=job_id, processed=processed_count, skipped=skipped_count)

            # Use final stats for the report
            final_processed_for_report = processed_count + skipped_count

            if final_processed_for_report == 0:
                 # Empty file case
                 error_msg = f"CSV file is empty or contains no valid records. Site: {auction_site}"
                 logger.error(error_msg, job_id=job_id)
                 await db.update_csv_upload_progress( job_id=job_id, status='failed', error_message=error_msg )
                 return

            # 4. Merge Staging to Main (sequential merge 0→4)
            await db.update_csv_upload_progress(
                job_id=job_id,
                status='processing',
                current_stage='merging',
                processed_records=final_processed_for_report,
                skipped_count=skipped_count,
                error_message=error_message if skipped_count > 0 else None
            )

            # Use the same cleanup strategy as the Mark phase
            cleanup_type = offering_type
            if auction_site.lower() in ['godaddy', 'namesilo']:
                cleanup_type = None

            # Sequential merge (table 0→4)
            total_merged = 0
            for staging_idx in range(NUM_STAGING_TABLES):
                table_name = get_staging_table_name(staging_idx)
                logger.info(f"Merging staging table {table_name}", job_id=job_id)

                try:
                    merged = await _perform_rpc_merge(db, auction_site, job_id, staging_idx, cleanup_type)
                    total_merged += merged
                    logger.info(f"Merged {table_name}", job_id=job_id, count=merged)
                except Exception as merge_err:
                    logger.error(f"Merge failed for {table_name}", job_id=job_id, error=str(merge_err))
                    raise

            logger.info("All staging tables merged", job_id=job_id, total_merged=total_merged)

            # =====================================================
            # POST-MERGE SCORING: Score only NEW domains (fast!)
            # Existing domains kept their score, new domains have NULL score
            # =====================================================
            await db.update_csv_upload_progress(
                job_id=job_id,
                status='processing',
                current_stage='scoring_new',
                processed_records=final_processed_for_report
            )

            scoring_service = DomainScoringService()
            scored_new_count = await _score_new_domains_after_merge(
                db, auction_site, scoring_service, job_id,
                fast_mode=(auction_site.lower() == 'namecheap')
            )
            logger.info("Post-merge scoring complete", job_id=job_id, new_domains_scored=scored_new_count)

            # 5. Success
            end_mem = process.memory_info().rss / 1024 / 1024 if 'process' in locals() and process else None
            logger.info(f"[CSV UPLOAD COMPLETE] {job_id}", processed=processed_count, skipped=skipped_count, merged=total_merged, end_memory_mb=end_mem)
            await db.update_csv_upload_progress( job_id=job_id, status='completed', current_stage='completed', processed_records=processed_count, skipped_count=skipped_count, inserted_count=total_merged, completed=True )

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"[CSV UPLOAD FAILED] {job_id}", error=str(e), traceback=error_detail[:2000])
        await db.update_csv_upload_progress( job_id=job_id, status='failed', error_message=f"Failed: {str(e)[:500]}" )


async def process_json_upload_async( job_id: str, json_content: str, filename: str, auction_site: str, offering_type: Optional[str] = None, is_file: bool = False ):
    """
    Background task to process JSON upload with progress tracking
    """
    # Optional memory tracking
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        start_mem = process.memory_info().rss / 1024 / 1024
        logger.info(f"[JSON UPLOAD START] {job_id}", filename=filename, auction_site=auction_site, offering_type=offering_type, start_memory_mb=start_mem)
    except ImportError:
        logger.info(f"[JSON UPLOAD START] {job_id}", filename=filename, auction_site=auction_site, offering_type=offering_type)
        start_mem = None

    db = get_database()
    auctions_service = AuctionsService()

    try:
        # Check if another upload is running and mark as queued if so
        if _upload_status_lock.locked():
            logger.info("[JSON UPLOAD] Another upload is in progress, queuing job", job_id=job_id)
            try:
                await db.update_csv_upload_progress(job_id=job_id, status='queued', current_stage='waiting_for_lock')
            except Exception as e:
                logger.error(f"[JSON UPLOAD] Failed to update queued status: {e}", job_id=job_id)

        async with _upload_status_lock:
            # Update status to parsing
            await db.update_csv_upload_progress( job_id=job_id, status='parsing', current_stage='parsing' )
            
            # Parse JSON using auctions service
            logger.info(f"[JSON UPLOAD] Starting JSON parse", job_id=job_id, auction_site=auction_site, filename=filename, is_file=is_file)
            try:
                auction_inputs = auctions_service.load_auctions_from_json(json_content, auction_site, filename, is_file=is_file)
            except Exception as parse_err:
                logger.error(f"[JSON UPLOAD PARSE ERROR] {job_id}", error=str(parse_err), auction_site=auction_site)
                await db.update_csv_upload_progress( job_id=job_id, status='failed', error_message=f"JSON parse error: {str(parse_err)[:500]}" )
                return

            if not auction_inputs:
                error_msg = f"JSON file is empty or contains no valid auction records. Auction site: {auction_site}, Filename: {filename}"
                logger.error(f"[JSON UPLOAD] {error_msg}", job_id=job_id)
                await db.update_csv_upload_progress( job_id=job_id, status='failed', error_message=error_msg )
                return

            total_records = len(auction_inputs)
            logger.info(f"[JSON UPLOAD] Parsed successfully", job_id=job_id, total_records=total_records)

            # Update status to processing
            await db.update_csv_upload_progress( job_id=job_id, status='processing', total_records=total_records, current_stage='scoring' )
        
        # Initialize scoring service
        scoring_service = DomainScoringService()
        
        # Convert to database format with scoring
        auction_dicts = []
        skipped_count = 0
        scored_count = 0
        passed_count = 0
        failed_count = 0
        
        for idx, auction_input in enumerate(auction_inputs):
            try:
                auction = auction_input.to_auction()
                
                # Determine offer_type
                record_offer_type = offering_type or 'auction'

                # For GoDaddy, check auctionType from source_data
                if auction_site.lower() == 'godaddy' and auction.source_data:
                    auction_type = auction.source_data.get('auctionType', '').strip()
                    if auction_type.lower() == 'buynow':
                        record_offer_type = 'buy_now'
                    elif auction_type.lower() == 'bid':
                        record_offer_type = 'auction'
                
                # Convert to NamecheapDomain for scoring
                source_data = auction.source_data or {}
                registered_date = None
                if isinstance(source_data, dict):
                    reg_date = (source_data.get('registered_date') or 
                               source_data.get('registeredDate') or
                               source_data.get('Registered Date') or
                               source_data.get('registered date'))
                    if reg_date:
                        if isinstance(reg_date, str) and reg_date.strip():
                                registered_date = reg_date # Fallback or parse if needed
                        elif isinstance(reg_date, datetime):
                            registered_date = reg_date
                
                namecheap_domain = NamecheapDomain( name=auction.domain, registered_date=registered_date, url=None, start_date=auction.start_date, end_date=auction.expiration_date, price=None )
                
                # Score domain
                scored = scoring_service.score_domain(namecheap_domain)
                scored_count += 1
                
                score_value = scored.total_meaning_score if scored.total_meaning_score is not None else None
                
                auction_dict = { 'domain': auction.domain, 'start_date': auction.start_date.isoformat() if auction.start_date else None, 'expiration_date': auction.expiration_date.isoformat() if auction.expiration_date else None, 'auction_site': auction.auction_site, 'current_bid': auction.current_bid, 'source_data': auction.source_data, 'link': auction.link, 'processed': True, 'preferred': False, 'has_statistics': False, 'score': score_value, 'ranking': None, 'offer_type': record_offer_type, 'job_id': job_id }
                
                
                if scored.filter_status == 'PASS':
                    passed_count += 1
                else:
                    failed_count += 1
                
                auction_dicts.append(auction_dict)

                # Yield control to the event loop frequently to prevent blocking UVicorn and causing 502 timeouts
                if idx % 100 == 0:
                    await asyncio.sleep(0)
            except Exception as e:
                skipped_count += 1
                # Log first 5 errors for debugging
                if skipped_count <= 5:
                    logger.warning(f"[JSON UPLOAD] Scoring error for item {idx}", domain=auction_input.domain if hasattr(auction_input, 'domain') else 'unknown', error=str(e))
                continue

            # Keep event loop responsive for health checks
            if (idx + 1) % 500 == 0:
                await asyncio.sleep(0.01)

            # Log progress every 5000 records for large files
            if (idx + 1) % 5000 == 0:
                logger.info(f"[JSON UPLOAD] Scoring progress", job_id=job_id, processed=idx+1, total=total_records, passed=passed_count, failed=failed_count)

            if (idx + 1) % 1000 == 0:
                await db.update_csv_upload_progress( job_id=job_id, processed_records=idx + 1, skipped_count=skipped_count, current_stage='scoring' )

        # Update stage
        logger.info(f"[JSON UPLOAD] Scoring complete", job_id=job_id, total=total_records, passed=passed_count, failed=failed_count, skipped=skipped_count, ready_for_staging=len(auction_dicts))
        await db.update_csv_upload_progress( job_id=job_id, processed_records=len(auction_dicts), skipped_count=skipped_count, current_stage='loading_staging' )

        # Loading and Merging (simplified logic)
        if db.client:
             effective_offering_type = offering_type or 'auction'
             
             # General "Mark & Sweep" cleanup logic - Mark Phase
             try:
                 # site-specific cleanup strategy
                 cleanup_type = effective_offering_type
                 if auction_site.lower() in ['godaddy', 'namesilo']:
                     cleanup_type = None
                     
                 await _mark_auctions_for_deletion(db, auction_site, cleanup_type)
             except Exception as e:
                 logger.warning("Failed to mark records for deletion, continuing", job_id=job_id, error=str(e))

             # Clear ALL 5 staging tables for this job_id
             try:
                 await _clear_all_staging_tables_chunked(db, job_id)
             except Exception as e:
                 logger.warning("Failed to clear staging tables, continuing", job_id=job_id, error=str(e))

             # Partition records across 5 staging tables
             partitioned = {i: [] for i in range(NUM_STAGING_TABLES)}
             for record in auction_dicts:
                 staging_idx = get_staging_table_index(record.get('domain', ''))
                 partitioned[staging_idx].append(record)

             # Parallel insert to 5 staging tables using asyncio.gather
             async def insert_to_staging(index: int, records: list) -> int:
                 if not records:
                     return 0
                 table_name = get_staging_table_name(index)
                 client = await db._get_client()

                 # Add job_id to each record
                 for r in records:
                     r['job_id'] = job_id

                 batch_size = 500
                 for i in range(0, len(records), batch_size):
                     batch = records[i:i + batch_size]
                     for attempt in range(3):
                         try:
                             await client.table(table_name).insert(batch).execute()
                             break
                         except Exception:
                             if attempt == 2:
                                 raise
                             await asyncio.sleep(2 ** attempt)
                     await asyncio.sleep(0.01)

                 return len(records)

             # Execute parallel inserts
             insert_tasks = [insert_to_staging(i, partitioned[i]) for i in range(NUM_STAGING_TABLES)]
             insert_results = await asyncio.gather(*insert_tasks, return_exceptions=True)

             # Check for failures
             for i, result in enumerate(insert_results):
                 if isinstance(result, Exception):
                     logger.error(f"JSON parallel insert failed for table {i}", job_id=job_id, error=str(result))
                     await _clear_all_staging_tables_chunked(db, job_id)
                     raise result

             logger.info(f"[JSON UPLOAD] Parallel insert complete", job_id=job_id)

             # Sequential merge (table 0→4) using RPC
             total_merged = 0
             for staging_idx in range(NUM_STAGING_TABLES):
                 try:
                     merged = await _perform_rpc_merge(db, auction_site, job_id, staging_idx, cleanup_type)
                     total_merged += merged
                     logger.info(f"[JSON UPLOAD] Merged table {staging_idx}", job_id=job_id, count=merged)
                 except Exception as merge_err:
                     logger.error(f"[JSON UPLOAD] Merge failed for table {staging_idx}", job_id=job_id, error=str(merge_err))
                     raise

             logger.info(f"[JSON UPLOAD MERGE] {job_id}", merged=total_merged, total=total_records)

        # Final update
        end_mem = process.memory_info().rss / 1024 / 1024 if 'process' in locals() and process else None
        logger.info(f"[JSON UPLOAD COMPLETE] {job_id}", total=total_records, merged=total_merged, end_memory_mb=end_mem)
        await db.update_csv_upload_progress( job_id=job_id, status='completed', current_stage='completed', processed_records=total_records, inserted_count=total_merged, completed=True )
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"[JSON UPLOAD FAILED] {job_id}", error=str(e), traceback=error_detail[:2000])
        await db.update_csv_upload_progress( job_id=job_id, status='failed', error_message=f"Failed: {str(e)[:500]}" )





@router.post("/auctions/upload-csv")
async def upload_auctions_csv( background_tasks: BackgroundTasks, file: UploadFile = File(...), auction_site: str = Query(..., description="Auction site name (e.g., namecheap, godaddy)"), offering_type: str = Query('auction', description="Offering type (auction, backorder, buy_now)"), ):
    """
    Upload auctions CSV file. This endpoint:
    1. Saves the file to a temporary location immediately
    2. Returns a success response to prevent N8N timeouts
    3. Handles Supabase Storage upload and processing in the background
    """
    import tempfile
    import os
    
    try:
        # Validate file
        filename = file.filename.lower()
        if not (filename.endswith('.csv') or filename.endswith('.json')):
            raise HTTPException(status_code=400, detail="File must be a CSV or JSON")
        
        # Generator for unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{auction_site}_{timestamp}_{file.filename}"
        job_id = str(uuid.uuid4())
        
        # Save to temp file immediately
        fd, temp_path = tempfile.mkstemp(suffix=f"_{safe_filename}")
        
        # Read and write content
        content = await file.read()
        with os.fdopen(fd, 'wb') as tmp:
            tmp.write(content)
            
        # ) Create job entry (so we have a record even before processing starts
        db = get_database()
        await db.create_csv_upload_job( job_id=job_id, filename=safe_filename, auction_site=auction_site, offering_type=offering_type )
        
        # Start background task that handles BOTH upload to storage AND processing
        background_tasks.add_task( background_handle_upload_and_process, job_id=job_id, local_path=temp_path, filename=safe_filename, auction_site=auction_site, offering_type=offering_type )
        
        logger.info("File accepted for async processing", filename=safe_filename, job_id=job_id, temp_path=temp_path)
            
        return { "success": True, "message": "File accepted. Upload to storage and processing started in background.", "filename": safe_filename, "job_id": job_id, "n8n_triggered": False }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to initiate upload", error=str(e))
        raise HTTPException(status_code=500, detail=f"Upload initiation failed: {str(e)}")

class StorageProcessingRequest(BaseModel):
    storage_path: str
    filename: str
    auction_site: str
    offering_type: Optional[str] = 'auction'
    bucket: Optional[str] = "auction-csvs"

@router.post("/auctions/process-existing-upload")
async def process_existing_upload( request: StorageProcessingRequest ):
    """
    Trigger processing for a file already uploaded to Supabase Storage. Use this to bypass backend upload limits/timeouts. Upload directly to Supabase Storage from client (e.g. N8N), then call this. """
    try:
        job_id = str(uuid.uuid4())

        # ) Start background processing using asyncio.create_task (proper for async functions
        # BackgroundTasks.add_task is for sync functions only and can swallow exceptions
        asyncio.create_task( process_file_from_storage_async( job_id=job_id, bucket=request.bucket, path=request.storage_path, filename=request.filename, auction_site=request.auction_site, offering_type=request.offering_type ) )

        logger.info("Triggered processing for existing storage file", filename=request.filename, job_id=job_id, storage_path=request.storage_path)

        # Return immediately - the background task runs after response is sent
        return { "success": True, "message": "Processing started in background.", "job_id": job_id, "filename": request.filename }

    except Exception as e:
        logger.error("Failed to trigger storage processing", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to trigger processing: {str(e)}")


@router.post("/auctions/trigger-processing-async")
async def trigger_processing_async( request: StorageProcessingRequest ):
    """
    Fire-and-forget endpoint to trigger auction file processing. This endpoint returns immediately (202 Accepted) and processes the file
    in a completely detached background task. Use this from N8N or other
    automation tools to avoid timeouts. The processing status can be checked via /auctions/upload-progress/{job_id}
    """
    job_id = str(uuid.uuid4())

    # Create detached background task - runs completely independently
    asyncio.create_task( _process_file_detached( job_id=job_id, bucket=request.bucket, path=request.storage_path, filename=request.filename, auction_site=request.auction_site, offering_type=request.offering_type ) )

    # Yield control to ensure the task is scheduled and response is flushed
    await asyncio.sleep(0)

    logger.info("Detached processing triggered", filename=request.filename, job_id=job_id, storage_path=request.storage_path)

    # Return immediately - 202 Accepted
    return { "success": True, "message": "Processing started in background.", "job_id": job_id, "filename": request.filename, "status": "accepted" }




async def _process_file_detached( job_id: str, bucket: str, path: str, filename: str, auction_site: str, offering_type: Optional[str] = None ):
    """
    Wrapper to run process_file_from_storage_async in a detached task
    with proper error handling. """
    try:
        await process_file_from_storage_async( job_id=job_id, bucket=bucket, path=path, filename=filename, auction_site=auction_site, offering_type=offering_type )
    except Exception as e:
        logger.error("Detached processing failed", job_id=job_id, error=str(e), exc_info=True)


class NameSiloActiveSalesRequest(BaseModel):
    """Request model for NameSilo active sales data"""
    sales_data: List[Dict[str, Any]]
    filename: Optional[str] = "namesilo_active_sales.csv"
    offering_type: Optional[str] = "buy_now"


@router.post("/auctions/process-namesilo-active-sales")
async def process_namesilo_active_sales( request: NameSiloActiveSalesRequest ):
    """
    Process NameSilo active sales data directly from API. Accepts JSON data from NameSilo marketplaceActiveSalesOverview API, converts it to CSV format, and processes it like a regular upload. The sales_data should be the 'sale_details' array from the NameSilo response. """
    job_id = str(uuid.uuid4())

    try:
        # Convert NameSilo data to CSV format
        csv_rows = []

        # Header row
        headers = [ "Domain", "Status", "Reserve", "Buy_Now", "Portfolio", "Sale_Type", "Pay_Plan_Offered", "End_Date", "Auto_Extend_Days", "Time_Remaining", "Private", "Active_Bid_Or_Offer"
        ]
        csv_rows.append(",".join(f'"{h}"' for h in headers))

        # Data rows
        for sale in request.sales_data:
            row = [ sale.get("domain", ""), sale.get("status", ""), sale.get("reserve", ""), sale.get("buy_now", ""), sale.get("portfolio", ""), sale.get("sale_type", ""), sale.get("pay_plan_offered", ""), sale.get("end_date", ""), sale.get("auto_extend_days", ""), sale.get("time_remaining", ""), sale.get("private", ""), sale.get("active_bid_or_offer", "")
            ]
            # Escape quotes and wrap in quotes
            escaped_row = ['"' + str(cell).replace('"', '""') + '"' for cell in row]
            csv_rows.append(",".join(escaped_row))

        csv_content = "\n".join(csv_rows)

        # Create detached background task to process the CSV
        asyncio.create_task( _process_namesilo_sales_detached( job_id=job_id, csv_content=csv_content, filename=request.filename, offering_type=request.offering_type ) )

        # Yield control to ensure the task is scheduled
        await asyncio.sleep(0)

        logger.info("NameSilo active sales processing triggered", job_id=job_id, record_count=len(request.sales_data), filename=request.filename)

        return { "success": True, "message": "NameSilo active sales processing started in background.", "job_id": job_id, "filename": request.filename, "record_count": len(request.sales_data), "status": "accepted" }

    except Exception as e:
        logger.error("Failed to process NameSilo active sales", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process NameSilo sales: {str(e)}")


async def _process_namesilo_sales_detached( job_id: str, csv_content: str, filename: str, offering_type: Optional[str] = None ):
    """
    Background task to upload NameSilo sales CSV to storage and process it. """
    import tempfile
    import os

    temp_path = None

    try:
        db = get_database()

        # Create temp file
        safe_filename = filename.replace('/', '_').replace('\\', '_')
        temp_fd, temp_path = tempfile.mkstemp(suffix=f"_{safe_filename}")
        os.close(temp_fd)

        # Write CSV content
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        # Upload to storage
        with open(temp_path, 'rb') as f:
            file_content = f.read()

        storage_path = await db.upload_csv_to_storage(file_content, filename)
        logger.info("NameSilo sales uploaded to storage", job_id=job_id, storage_path=storage_path)

        # Process the file
        await process_csv_upload_async( job_id=job_id, csv_content=temp_path, filename=filename, auction_site="namesilo", offering_type=offering_type, is_file=True )

    except Exception as e:
        logger.error("Failed to process NameSilo sales in background", job_id=job_id, error=str(e), exc_info=True)
        try:
            db = get_database()
            await db.update_csv_upload_progress( job_id=job_id, status='failed', error_message=str(e) )
        except:
            pass
    finally:
        # Cleanup temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


async def background_handle_upload_and_process( job_id: str, local_path: str, filename: str, auction_site: str, offering_type: str ):
    """
    Handles the full background lifecycle:
    1. Upload local temp file to Supabase Storage
    2. Trigger processing using the local file (avoiding re-download)
    3. Cleanup
    """
    import os
    
    try:
        db = get_database()
        
        # 1. Upload to Storage
        logger.info("Starting background storage upload", job_id=job_id, filename=filename)
        
        # Read file content for upload
        # Note: This might use memory for large files, but is consistent with previous behavior
        with open(local_path, "rb") as f:
            file_content = f.read()
            
        storage_path = await db.upload_csv_to_storage(file_content, filename)
        logger.info("Background storage upload complete", job_id=job_id, storage_path=storage_path)
        
        # ) 2. Process (using local path
        is_json = filename.lower().endswith('.json')
        is_csv = filename.lower().endswith('.csv')
        
        if is_json:
            await process_json_upload_async( job_id=job_id, json_content=local_path, filename=filename, auction_site=auction_site, offering_type=offering_type, is_file=True )
        elif is_csv:
            await process_csv_upload_async( job_id=job_id, csv_content=local_path, filename=filename, auction_site=auction_site, offering_type=offering_type, is_file=True )
            
    except Exception as e:
        logger.error("Background upload/processing failed", job_id=job_id, error=str(e), exc_info=True)
        try:
            db = get_database()
            await db.update_csv_upload_progress( job_id=job_id, status='failed', error_message=str(e) )
        except:
            pass
            
    finally:
        # 3. Cleanup temp file
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
                logger.info("Cleaned up temp upload file", local_path=local_path)
        except Exception as e:
            logger.warning("Failed to cleanup temp file", path=local_path, error=str(e))



@router.post("/auctions/upload-json")
async def upload_auctions_json( file: UploadFile = File(...), auction_site: str = Query(..., description="Auction site source: 'godaddy', etc."), offering_type: Optional[str] = Query(None, description="Type of domain offering: 'auction', 'backorder', 'buy_now'"), background_tasks: BackgroundTasks = BackgroundTasks() ):
    """
    Upload JSON file and process it asynchronously with progress tracking
    
    This will:
    1. Create a job and return job_id immediately
    2. Process JSON in background: parse, convert, upsert (update existing, add new), delete expired
    3. Use /auctions/upload-progress/{job_id} to check progress
    
    Returns:
        Job ID for tracking progress
    """
    try:
        # Auto-detect auction_site from filename if not provided or if filename contains site name
        detected_site = auction_site.lower().strip() if auction_site and auction_site.lower() != 'auto' else 'godaddy'
        detected_offering_type = offering_type
        
        if file.filename:
            filename_lower = file.filename.lower()
            if 'godaddy' in filename_lower or 'go_daddy' in filename_lower:
                detected_site = 'godaddy'
                # Default Godaddy to auction if not specified
                if not detected_offering_type:
                    detected_offering_type = 'auction'
        
        # Set default to 'auction' if not detected
        if not detected_offering_type:
            detected_offering_type = 'auction'
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Read file content in chunks to handle large files
        content_chunks = []
        total_size = 0
        chunk_size = 1024 * 1024  # 1MB chunks
        
        logger.info("Starting JSON upload", job_id=job_id, filename=file.filename, auction_site=detected_site)
        
        # Read file in chunks
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            content_chunks.append(chunk)
            total_size += len(chunk)
            logger.debug("Read chunk", chunk_size=len(chunk), total_size=total_size)
        
        # Combine chunks and decode to string
        content_bytes = b''.join(content_chunks)
        file_size_mb = round(total_size / (1024 * 1024), 2)
        
        logger.info("Received auctions JSON upload", job_id=job_id, filename=file.filename, size=total_size, size_mb=file_size_mb, auction_site=detected_site)
        
        # Decode JSON content
        try:
            json_content = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            # Try other encodings
            try:
                json_content = content_bytes.decode('latin-1')
            except UnicodeDecodeError:
                json_content = content_bytes.decode('utf-8', errors='replace')
                logger.warning("Used UTF-8 with error replacement for JSON decoding")
        
        # Validate JSON format
        try:
            import json
            json.loads(json_content)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON format: {str(e)}"
            logger.error("Invalid JSON format", job_id=job_id, error=error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Create progress tracking job
        db = get_database()
        await db.create_csv_upload_job( job_id=job_id, filename=file.filename, auction_site=detected_site )
        
        # Start background processing
        background_tasks.add_task( process_json_upload_async, job_id=job_id, json_content=json_content, filename=file.filename, auction_site=detected_site, offering_type=detected_offering_type )
        
        return { "success": True, "job_id": job_id, "message": "JSON upload started. Use /auctions/upload-progress/{job_id} to check progress.", "filename": file.filename, "auction_site": detected_site }
        
    except HTTPException:
        raise
    except MemoryError:
        logger.error("Out of memory while processing JSON", filename=file.filename)
        raise HTTPException( status_code=413, detail="File is too large to process. Please split the file into smaller chunks or contact support." )
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        logger.error("Failed to upload auctions JSON", error=error_msg, error_type=error_type, filename=file.filename, exc_info=True)
        
        # Provide more helpful error messages
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            detail = f"Upload timed out. The file may be too large. Please try again or split into smaller files. Error: {error_msg}"
        elif "too large" in error_msg.lower() or "size" in error_msg.lower():
            detail = f"File is too large. Please split into smaller files. Error: {error_msg}"
        elif "memory" in error_msg.lower():
            detail = f"Insufficient memory to process file. Please split into smaller files. Error: {error_msg}"
        else:
            detail = f"Failed to process JSON: {error_msg}"
        
        raise HTTPException(status_code=500, detail=detail)


async def process_file_from_storage_async( job_id: str, bucket: str, path: str, filename: str, auction_site: str, offering_type: Optional[str] = None ):
    """
    Background task to download and process file from storage using streaming and temp files
    """
    import tempfile
    import os
    
    temp_path = None
    
    try:
        db = get_database()
        
        # ) Create progress tracking job (moved from endpoint to prevent timeouts
        await db.create_csv_upload_job( job_id=job_id, filename=filename, auction_site=auction_site, offering_type=offering_type )
        
        # ) Sanitize filename for temp file usage (replace slashes with underscores
        # This prevents "No such file or directory" errors if filename contains folders
        safe_filename = filename.replace('/', '_').replace('\\', '_')
        
        # Create a unique temp file path
        # We do this INSIDE the try block to catch any FS errors
        temp_fd, temp_path = tempfile.mkstemp(suffix=f"_{safe_filename}")
        os.close(temp_fd) # Close file descriptor, we'll open it by path
        
        # Update status to downloading
        await db.update_csv_upload_progress( job_id=job_id, status='downloading', current_stage='downloading_from_storage' )
        
        # Download file to temp disk location
        logger.info("Downloading file from storage to temp disk", job_id=job_id, bucket=bucket, path=path, local_path=temp_path)
        
        file_size = await db.download_to_file(bucket, path, temp_path)
        
        if file_size == 0:
            logger.warning("Downloaded empty file", job_id=job_id, path=path)
            # We continue processing, parser will handle empty file
        
        # Determine file type and process
        is_json = filename.lower().endswith('.json')
        is_csv = filename.lower().endswith('.csv')
        
        if is_json:
            # Process JSON using the file path
            await process_json_upload_async( job_id=job_id, json_content=temp_path, filename=filename, auction_site=auction_site, offering_type=offering_type, is_file=True )
        elif is_csv:
            # Process CSV using the file path
            await process_csv_upload_async( job_id=job_id, csv_content=temp_path, filename=filename, auction_site=auction_site, offering_type=offering_type, is_file=True )
        else:
            await db.update_csv_upload_progress( job_id=job_id, status='failed', error_message="File must be CSV or JSON" )
            logger.error("Invalid file type", job_id=job_id, filename=filename)
        
        # Check job status and delete file from storage if successful
        try:
            job_status = await db.get_csv_upload_progress(job_id)
            if job_status and job_status.get('status') == 'completed':
                logger.info("Job completed successfully, deleting file from storage", job_id=job_id, bucket=bucket, path=path)
                await db.delete_file_from_storage(bucket, path)
            else:
                logger.info("Job did not complete successfully, keeping file in storage", job_id=job_id, status=job_status.get('status') if job_status else 'unknown', bucket=bucket, path=path)
        except Exception as cleanup_error:
            logger.warning("Failed to perform storage cleanup check", job_id=job_id, error=str(cleanup_error))
            
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to process file from storage", job_id=job_id, bucket=bucket, path=path, error=error_msg, exc_info=True)
        
        try:
            db = get_database()
            # If job exists, update it. If create_job failed, this might also fail or update non-existent job. # But mostly create_job succeeds, and error happens later.
            await db.update_csv_upload_progress( job_id=job_id, status='failed', error_message=f"Storage processing failed: {error_msg}" )
        except:
            pass
            
    finally:
        # ALWAYS clean up the temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info("Cleaned up temp processing file", local_path=temp_path)
            except Exception as e:
                logger.warning("Failed to remove temp file", local_path=temp_path, error=str(e))


@router.post("/auctions/process-from-storage")
async def process_from_storage( bucket: str = Body(..., description="Supabase storage bucket name"), path: str = Body(..., description="File path in storage"), auction_site: str = Body(..., description="Auction site source"), offering_type: Optional[str] = Body(None, description="Type of domain offering"), filename: Optional[str] = Body(None, description="Original filename") ):
    """
    Process auction file from Supabase storage

    Returns immediately and processes the file in the background to avoid ngrok timeouts. Downloads the file from storage and processes it (CSV or JSON)
    """
    try:
        # Determine file type from path/filename
        file_path = filename or path
        is_json = file_path.lower().endswith('.json')
        is_csv = file_path.lower().endswith('.csv')

        if not (is_json or is_csv):
            raise HTTPException(status_code=400, detail="File must be CSV or JSON")

        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # ) Start background task using asyncio.create_task (proper for async functions
        # BackgroundTasks.add_task is for sync functions only and can swallow exceptions
        asyncio.create_task( process_file_from_storage_async( job_id=job_id, bucket=bucket, path=path, filename=file_path, auction_site=auction_site, offering_type=offering_type ) )

        logger.info("File processing started in background", job_id=job_id, bucket=bucket, path=path)

        return { "success": True, "job_id": job_id, "message": f"{'JSON' if is_json else 'CSV'} processing started from storage. Use /auctions/upload-progress/{job_id} to check progress.", "filename": file_path, "auction_site": auction_site, "bucket": bucket, "path": path }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to initiate file processing from storage", bucket=bucket, path=path, error=error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to initiate file processing: {error_msg}")


@router.get("/auctions/upload-progress/latest-active")
async def get_latest_active_upload_progress():
    """
    Get the latest active (non-completed, non-failed) CSV upload job progress
    
    Returns:
        Progress information for the latest active job, or 404 if no active job found
    """
    try:
        db = get_database()
        progress = await db.get_latest_active_upload_job()
        
        if not progress:
            raise HTTPException( status_code=404, detail="No active upload job found" )
        
        job_id = progress.get('job_id')
        return { "success": True, "job_id": job_id, "status": progress.get('status'), "filename": progress.get('filename'), "auction_site": progress.get('auction_site'), "total_records": progress.get('total_records', 0), "processed_records": progress.get('processed_records', 0), "inserted_count": progress.get('inserted_count', 0), "updated_count": progress.get('updated_count', 0), "skipped_count": progress.get('skipped_count', 0), "deleted_expired_count": progress.get('deleted_expired_count', 0), "current_stage": progress.get('current_stage'), "progress_percentage": progress.get('progress_percentage', 0.00), "error_message": progress.get('error_message'), "started_at": progress.get('started_at'), "updated_at": progress.get('updated_at'), "completed_at": progress.get('completed_at') }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get latest active upload progress", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get latest active progress: {str(e)}")


@router.get("/auctions/upload-progress/{job_id}")
async def get_upload_progress(job_id: str):
    """
    Get progress status for a CSV upload job
    
    Args:
        job_id: Job identifier returned from upload endpoint
        
    Returns:
        Progress information including status, counts, and percentage
    """
    try:
        db = get_database()
        progress = await db.get_csv_upload_progress(job_id)
        
        if not progress:
            raise HTTPException( status_code=404, detail=f"Job {job_id} not found" )
        
        return { "success": True, "job_id": job_id, "status": progress.get('status'), "filename": progress.get('filename'), "auction_site": progress.get('auction_site'), "total_records": progress.get('total_records', 0), "processed_records": progress.get('processed_records', 0), "inserted_count": progress.get('inserted_count', 0), "updated_count": progress.get('updated_count', 0), "skipped_count": progress.get('skipped_count', 0), "deleted_expired_count": progress.get('deleted_expired_count', 0), "current_stage": progress.get('current_stage'), "progress_percentage": progress.get('progress_percentage', 0.00), "error_message": progress.get('error_message'), "started_at": progress.get('started_at'), "updated_at": progress.get('updated_at'), "completed_at": progress.get('completed_at') }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get upload progress", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")


@router.post("/auctions/upload-progress/{job_id}/mark-failed")
async def mark_job_as_failed( job_id: str, request: Optional[Dict[str, Any]] = Body(default=None, description="Optional request body with error_message") ):
    """
    Manually mark an upload job as failed
    
    Useful for stuck jobs that need to be marked as failed to stop frontend polling
    """
    try:
        db = get_database()
        progress = await db.get_csv_upload_progress(job_id)
        
        if not progress:
            raise HTTPException( status_code=404, detail=f"Job {job_id} not found" )
        
        if progress.get('status') in ['completed', 'failed']:
            raise HTTPException( status_code=400, detail=f"Job is already {progress.get('status')}" )
        
        # Get error message from request body or use default
        error_msg = (request.get('error_message') if request else None) or "Job marked as failed manually (appears to be stuck)"
        
        # Mark as failed
        await db.update_csv_upload_progress( job_id=job_id, status='failed', error_message=error_msg, current_stage='failed' )
        
        logger.info("Job marked as failed manually", job_id=job_id, error_message=error_msg)
        
        return { "success": True, "message": f"Job {job_id} marked as failed", "job_id": job_id, "error_message": error_msg }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to mark job as failed", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to mark job as failed: {str(e)}")


@router.post("/auctions/upload-progress/{job_id}/reset")
async def reset_stuck_upload(job_id: str):
    """
    Fully reset a stuck or failed upload job for safe re-run.

    This:
    1. Calls cleanup_stuck_upload() SQL function to:
       - Delete unrecovered auction records (to_delete=TRUE) for the job's site
       - Clear all staging tables (auctions_staging + _0 through _4) for this job_id
    2. Resets the csv_upload_progress record to status=pending

    Safe to call multiple times — idempotent.
    """
    try:
        db = get_database()
        client = await db._get_client()

        # Call the atomic cleanup function
        result = await client.rpc('cleanup_stuck_upload', {'p_job_id': job_id}).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail=f"cleanup_stuck_upload returned no data for job {job_id}")

        cleanup_result = result.data[0] if isinstance(result.data, list) else result.data

        if not cleanup_result.get('success'):
            raise HTTPException(status_code=400, detail=cleanup_result.get('error', 'Cleanup failed'))

        logger.info("Reset stuck upload", job_id=job_id, cleanup=cleanup_result)
        return {
            "success": True,
            "message": f"Upload {job_id} fully reset and ready for re-run",
            "job_id": job_id,
            "deleted_auctions": cleanup_result.get('deleted_auctions', 0),
            "cleaned_staging": cleanup_result.get('cleaned_staging', [])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to reset stuck upload", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to reset upload: {str(e)}")


@router.post("/auctions/trigger-analysis")
async def trigger_auctions_analysis( limit: int = Query(100, description="Maximum number of unique domains to trigger (DataForSEO limit: 100 unique domains per request)", ge=1, le=100), current_user = Depends(get_current_user) ):
    """
    Trigger DataForSEO analysis for scored domains without page_statistics
    
    This will:
    1. Get up to 100 most recent scored domains without page_statistics (ordered by created_at DESC)
       Note: DataForSEO bulk_pages_summary API allows up to 1000 total targets, but only 100 unique domains
    2. Trigger DataForSEO bulk page summary via n8n webhook
    3. Webhook will update page_statistics field in auctions table
    4. Return list of triggered domains
    """
    try:
        logger.info("Triggering auctions analysis", limit=limit)
        
        auctions_service = AuctionsService()
        
        # ) Get scored auctions without page_statistics (most recent first
        auctions = auctions_service.get_scored_auctions_without_page_statistics(limit=limit)
        
        if not auctions:
            return { "success": True, "message": "No scored domains without page_statistics found", "triggered_count": 0, "skipped_count": 0, "triggered_domains": [] }
        
        domain_names = [a['domain'] for a in auctions]
        
        # --- Credit Deduction Logic ---
        db = get_database()
        pricing_service = PricingService()
        credits_service = CreditsService(db)
        
        # Calculate cost for syncing these domains
        total_cost = pricing_service.calculate_action_cost('stats_sync', len(domain_names))
        
        logger.info("Deducting credits for auctions analysis", user_id=str(current_user.id), domain_count=len(domain_names), cost=total_cost)
        
        # Deduct credits
        success = credits_service.deduct_credits( user_id=current_user.id, amount=total_cost, description=f"DataForSEO extraction for {len(domain_names)} domains", reference_id=f"sync_{int(datetime.now(timezone.utc).timestamp())}" )
        
        if not success:
            logger.warning("Insufficient credits for auctions analysis", user_id=str(current_user.id), cost=total_cost)
            raise HTTPException( status_code=402, detail=f"Insufficient credits. This action requires {total_cost} credits." )
        # ------------------------------
        
        # Trigger DataForSEO analysis via N8N webhook
        n8n_service = N8NService()
        n8n_result = n8n_service.trigger_bulk_page_summary_workflow(domain_names)
        
        if n8n_result:
            triggered_count = len(domain_names)
            logger.info("Triggered N8N workflow for bulk page summary", triggered=triggered_count, request_id=n8n_result.get('request_id'))
            
            return { "success": True, "message": f"Triggered analysis for {triggered_count} domains", "triggered_count": triggered_count, "skipped_count": 0, "triggered_domains": domain_names[:100],  # Return first 100 for display
                "request_id": n8n_result.get('request_id') }
        else:
            logger.warning("Failed to trigger N8N workflow", domains=len(domain_names))
            return { "success": False, "message": "Failed to trigger N8N workflow", "triggered_count": 0, "skipped_count": len(domain_names), "triggered_domains": [] }
        
    except Exception as e:
        logger.error("Failed to trigger auctions analysis", error=str(e))
        raise HTTPException( status_code=500, detail=f"Failed to trigger analysis: {str(e)}" )


@router.post("/auctions/trigger-bulk-rank")
async def trigger_bulk_rank_analysis( limit: int = Query(1000, description="Maximum number of domains to trigger (DataForSEO bulk rank limit: 1000 domains)", ge=1, le=1000) ):
    """
    Trigger DataForSEO bulk rank analysis for scored domains closest to expire
    
    This will:
    1. Get up to 1000 scored domains (score IS NOT NULL) that don't have rank data, closest to expire (ordered by expiration_date ASC)
    2. Trigger DataForSEO bulk rank via n8n webhook (less expensive than bulk page summary)
    3. Webhook will update page_statistics field in auctions table with rank data
    4. Return list of triggered domains
    """
    try:
        logger.info("Triggering bulk rank analysis", limit=limit)
        
        auctions_service = AuctionsService()
        
        # Get scored auctions closest to expire that don't have rank data
        auctions = auctions_service.get_scored_auctions_closest_to_expire(limit=limit)
        
        if not auctions:
            return { "success": True, "message": "No scored domains without rank found", "triggered_count": 0, "skipped_count": 0, "triggered_domains": [] }
        
        domain_names = [a['domain'] for a in auctions]
        
        # Trigger DataForSEO bulk rank analysis via N8N webhook
        n8n_service = N8NService()
        n8n_result = n8n_service.trigger_bulk_rank_workflow(domain_names)
        
        if n8n_result:
            triggered_count = len(domain_names)
            logger.info("Triggered N8N workflow for bulk rank", triggered=triggered_count, request_id=n8n_result.get('request_id'))
            
            return { "success": True, "message": f"Triggered bulk rank analysis for {triggered_count} domains", "triggered_count": triggered_count, "skipped_count": 0, "triggered_domains": domain_names[:100],  # Return first 100 for display
                "request_id": n8n_result.get('request_id') }
        else:
            logger.warning("Failed to trigger N8N bulk rank workflow", domains=len(domain_names))
            return { "success": False, "message": "Failed to trigger N8N bulk rank workflow", "triggered_count": 0, "skipped_count": len(domain_names), "triggered_domains": [] }
        
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to trigger auctions analysis", error=error_msg, limit=limit)
        
        # Check if it's a timeout or connection error
        if 'timeout' in error_msg.lower() or 'connection' in error_msg.lower() or 'reset' in error_msg.lower():
            raise HTTPException( status_code=504, detail=f"Database query timed out while fetching auctions. Error: {error_msg}" )
        
        raise HTTPException(status_code=500, detail=f"Failed to trigger analysis: {error_msg}")


@router.post("/auctions/trigger-bulk-traffic-data")
async def trigger_bulk_traffic_data_analysis( limit: int = Query(1000, description="Maximum number of domains to trigger (DataForSEO Labs API limit: 1000 domains per request)", ge=1, le=1000) ):
    """
    Trigger DataForSEO Labs API traffic data collection for scored domains closest to expire without traffic_data
    
    This will:
    1. Get up to 1000 scored domains closest to expire (ordered by expiration_date ASC) that don't have traffic_data
    2. Trigger DataForSEO Labs API bulk traffic batch via n8n webhook
    3. Webhook will update traffic_data field in auctions table
    4. Return list of triggered domains
    """
    try:
        logger.info("Triggering traffic data analysis", limit=limit)
        
        auctions_service = AuctionsService()
        
        # Get scored auctions closest to expire without traffic_data
        auctions = await auctions_service.get_scored_auctions_closest_to_expire_without_traffic_data(limit=limit)
        
        if not auctions:
            return { "success": True, "message": "No scored domains without traffic_data found", "triggered_count": 0, "skipped_count": 0, "triggered_domains": [] }
        
        domain_names = [a['domain'] for a in auctions]
        
        # Trigger DataForSEO Labs API traffic data collection via N8N webhook
        n8n_service = N8NService()
        n8n_result = await n8n_service.trigger_bulk_traffic_batch_workflow(domain_names)
        
        if n8n_result:
            triggered_count = len(domain_names)
            logger.info("Triggered N8N workflow for bulk traffic batch", triggered=triggered_count, request_id=n8n_result.get('request_id'))
            
            return { "success": True, "message": f"Triggered traffic data collection for {triggered_count} domains", "triggered_count": triggered_count, "skipped_count": 0, "triggered_domains": domain_names[:100],  # Return first 100 for display
                "request_id": n8n_result.get('request_id') }
        else:
            logger.warning("Failed to trigger N8N traffic data workflow", domains=len(domain_names))
            return { "success": False, "message": "Failed to trigger N8N traffic data workflow", "triggered_count": 0, "skipped_count": len(domain_names), "triggered_domains": [] }
        
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to trigger traffic data analysis", error=error_msg, limit=limit)
        
        # Check if it's a timeout or connection error
        if 'timeout' in error_msg.lower() or 'connection' in error_msg.lower() or 'reset' in error_msg.lower():
            raise HTTPException( status_code=504, detail=f"Database query timed out while fetching auctions. Error: {error_msg}" )
        
        raise HTTPException(status_code=500, detail=f"Failed to trigger traffic data analysis: {error_msg}")


@router.post("/auctions/trigger-bulk-spam-score")
async def trigger_bulk_spam_score_analysis( limit: int = Query(1000, description="Maximum number of domains to trigger (DataForSEO bulk spam score limit: 1000 domains)", ge=1, le=1000) ):
    """
    Trigger DataForSEO bulk spam score analysis for scored domains closest to expire
    
    This will:
    1. Get up to 1000 scored domains closest to expire (ordered by expiration_date ASC) that don't have spam score data
    2. Trigger DataForSEO bulk spam score via n8n webhook
    3. Webhook will update backlinks_spam_score field in auctions table
    4. Return list of triggered domains
    """
    try:
        logger.info("Triggering bulk spam score analysis", limit=limit)
        
        auctions_service = AuctionsService()
        
        # Get scored auctions closest to expire that don't have spam score data
        auctions = await auctions_service.get_auctions_without_spam_score_closest_to_expire(limit=limit)
        
        if not auctions:
            return { "success": True, "message": "No scored domains without spam score found", "triggered_count": 0, "skipped_count": 0, "triggered_domains": [] }
        
        domain_names = [a['domain'] for a in auctions]
        
        # Trigger DataForSEO bulk spam score analysis via N8N webhook
        n8n_service = N8NService()
        n8n_result = n8n_service.trigger_bulk_spam_score_workflow(domain_names)
        
        if n8n_result:
            triggered_count = len(domain_names)
            logger.info("Triggered N8N workflow for bulk spam score", triggered=triggered_count, request_id=n8n_result.get('request_id'))
            
            return { "success": True, "message": f"Triggered bulk spam score analysis for {triggered_count} domains", "triggered_count": triggered_count, "skipped_count": 0, "triggered_domains": domain_names[:100],  # Return first 100 for display
                "request_id": n8n_result.get('request_id') }
        else:
            logger.warning("Failed to trigger N8N bulk spam score workflow", domains=len(domain_names))
            return { "success": False, "message": "Failed to trigger N8N bulk spam score workflow", "triggered_count": 0, "skipped_count": len(domain_names), "triggered_domains": [] }
        
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to trigger bulk spam score analysis", error=error_msg, limit=limit)
        
        # Check if it's a timeout or connection error
        if 'timeout' in error_msg.lower() or 'connection' in error_msg.lower() or 'reset' in error_msg.lower():
            raise HTTPException( status_code=504, detail=f"Database query timed out while fetching auctions. Error: {error_msg}" )
        
        raise HTTPException(status_code=500, detail=f"Failed to trigger bulk spam score analysis: {error_msg}")


@router.post("/auctions/trigger-bulk-backlinks")
async def trigger_bulk_backlinks_analysis( limit: int = Query(1000, description="Maximum number of domains to trigger (DataForSEO bulk backlinks limit: 1000 domains)", ge=1, le=1000) ):
    """
    Trigger DataForSEO bulk backlinks analysis for scored domains closest to expire
    
    This will:
    1. Get up to 1000 scored domains closest to expire (ordered by expiration_date ASC) that don't have backlinks data
    2. Trigger DataForSEO bulk backlinks via n8n webhook
    3. Webhook will update backlinks field in auctions table
    4. Return list of triggered domains
    """
    try:
        logger.info("Triggering bulk backlinks analysis", limit=limit)
        
        auctions_service = AuctionsService()
        
        # Get scored auctions closest to expire that don't have backlinks data
        auctions = await auctions_service.get_auctions_without_backlinks_closest_to_expire(limit=limit)
        
        if not auctions:
            return { "success": True, "message": "No scored domains without backlinks found", "triggered_count": 0, "skipped_count": 0, "triggered_domains": [] }
        
        domain_names = [a['domain'] for a in auctions]
        
        # Trigger DataForSEO bulk backlinks analysis via N8N webhook
        n8n_service = N8NService()
        n8n_result = n8n_service.trigger_bulk_backlinks_workflow(domain_names)
        
        if n8n_result:
            triggered_count = len(domain_names)
            logger.info("Triggered N8N workflow for bulk backlinks", triggered=triggered_count, request_id=n8n_result.get('request_id'))
            
            return { "success": True, "message": f"Triggered bulk backlinks analysis for {triggered_count} domains", "triggered_count": triggered_count, "skipped_count": 0, "triggered_domains": domain_names[:100],  # Return first 100 for display
                "request_id": n8n_result.get('request_id') }
        else:
            logger.warning("Failed to trigger N8N bulk backlinks workflow", domains=len(domain_names))
            return { "success": False, "message": "Failed to trigger N8N bulk backlinks workflow", "triggered_count": 0, "skipped_count": len(domain_names), "triggered_domains": [] }
        
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to trigger bulk backlinks analysis", error=error_msg, limit=limit)
        
        # Check if it's a timeout or connection error
        if 'timeout' in error_msg.lower() or 'connection' in error_msg.lower() or 'reset' in error_msg.lower():
            raise HTTPException( status_code=504, detail=f"Database query timed out while fetching auctions. Error: {error_msg}" )
        
        raise HTTPException(status_code=500, detail=f"Failed to trigger bulk backlinks analysis: {error_msg}")

        raise HTTPException(status_code=500, detail=f"Failed to trigger bulk backlinks analysis: {error_msg}")


async def process_traffic_metrics_background_task(domains: list[str]):
    """
    Background task to fetch and save traffic metrics using DataForSEO Live API. """
    try:
        from services.external_apis import DataForSEOService
        from services.database import get_database

        service = DataForSEOService()
        db = get_database()

        logger.info("Starting background processing for traffic data", domains=len(domains))

        # ) Call Live API (this blocks this task but not the main thread
        # Note: This is a system operation, user_id is None. Cost will be tracked as system usage.
        items = await service.fetch_bulk_traffic_estimation_live(domains, user_id=None)
        
        if items:
            logger.info("Traffic data retrieved", count=len(items))
            
            success_count = 0
            for item in items:
                # "item" structure based on verification:
 # }  { "se_type": "google", "target": "google.com", "metrics": { "organic": { "etv": ..., "count": ...
                target = item.get('target')
                metrics = item.get('metrics', {})
                
                if target and metrics:
                    traffic_data = { "organic_traffic": metrics.get('organic', {}).get('etv', 0), "etv": metrics.get('organic', {}).get('etv', 0), "organic_keywords": metrics.get('organic', {}).get('count', 0), "traffic_timestamp": datetime.now(timezone.utc).isoformat() }
                    
                    # Update DB
                    await db.update_auction_traffic_data(target, traffic_data)
                    success_count += 1
            
            logger.info("Traffic data processing completed", success_count=success_count)
        else:
            logger.warning("No traffic data items returned")
        
    except Exception as e:
        logger.error("Background traffic processing failed", error=str(e))


async def trigger_full_analysis_background( domain_names: List[str], n8n_service: N8NService, user_id: str ):
    """
    Background task to trigger all four DataForSEO analyses sequentially. Errors in one don't stop the others. """
    logger = structlog.get_logger().bind(user_id=user_id, operation="bulk_trigger_background")
    logger.info("Starting background bulk analysis triggers", domain_count=len(domain_names))
    
    # 1. Traffic data (Batch workflow) - handles up to 1000 domains
    try:
        logger.info("Triggering bulk traffic analysis")
        await n8n_service.trigger_bulk_traffic_batch_workflow(domain_names)
    except Exception as e:
        logger.error("Failed to trigger traffic data analysis", error=str(e))
    
    # 2. Rank analysis - handles up to 1000 domains
    try:
        logger.info("Triggering bulk rank analysis")
        await n8n_service.trigger_bulk_rank_workflow(domain_names)
    except Exception as e:
        logger.error("Failed to trigger rank analysis", error=str(e))
        
    # 3. Backlinks analysis - handles up to 1000 domains
    try:
        logger.info("Triggering bulk backlinks analysis")
        await n8n_service.trigger_bulk_backlinks_workflow(domain_names)
    except Exception as e:
        logger.error("Failed to trigger backlinks analysis", error=str(e))
        
    # 4. Spam score analysis - handles up to 1000 domains
    try:
        logger.info("Triggering bulk spam score analysis")
        await n8n_service.trigger_bulk_spam_score_workflow(domain_names)
    except Exception as e:
        logger.error("Failed to trigger spam score analysis", error=str(e))
        
    logger.info("Background bulk analysis triggers completed", domain_count=len(domain_names))


@router.post("/auctions/trigger-bulk-all-metrics")
async def trigger_bulk_all_metrics_analysis( preferred: Optional[bool] = Query(None, description="Filter by preferred status"), auction_site: Optional[str] = Query(None, description="Filter by auction site"), offering_type: Optional[str] = Query(None, description="Filter by market type: 'auction', 'backorder', 'buy_now'"), tld: Optional[str] = Query(None, description="Filter by TLD extension (e.g., '.com', '.ai') - deprecated, use tlds"), tlds: Optional[str] = Query(None, description="Comma-separated list of TLDs (e.g., '.com,.io,.ai')"), has_statistics: Optional[bool] = Query(None, description="Filter by has_statistics"), scored: Optional[bool] = Query(None, description="Filter by scored status (has score)"), min_rank: Optional[int] = Query(None, description="Minimum ranking", ge=1), max_rank: Optional[int] = Query(None, description="Maximum ranking", ge=1), min_score: Optional[float] = Query(None, description="Minimum score", ge=0, le=100), max_score: Optional[float] = Query(None, description="Maximum score", ge=0, le=100), expiration_from_date: Optional[str] = Query(None, description="Filter by expiration date from (YYYY-MM-DD)"), expiration_to_date: Optional[str] = Query(None, description="Filter by expiration date to (YYYY-MM-DD)"), sort_by: str = Query("expiration_date", description="Field to sort by"), sort_order: str = Query("asc", description="Sort order (asc, desc)"), limit: int = Query(1000, description="Maximum number of domains to trigger (1000 per analysis type)", ge=1, le=1000), force_refresh: bool = Query(False, description="Force refresh even if some metrics already exist"), background_tasks: BackgroundTasks = BackgroundTasks(), current_user = Depends(get_current_user) ):
    """
    Trigger all four DataForSEO analyses (traffic, rank, backlinks, spam_score) for domains matching current filters
    
    This will:
    1. Find up to 1000 domains that:
       - Match all current filter criteria
       - Are missing ANY of the four metrics (traffic_data, rank, backlinks, spam_score)
       - For auctions: ordered by expiration_date ASC (closest to expire first)
       - For buy_now: ordered by current sort_by and sort_order parameters
    2. Trigger all four N8N workflows sequentially:
       - Traffic data analysis
       - Rank analysis
       - Backlinks analysis
       - Spam score analysis
    3. Return summary with counts for each triggered analysis
    """
    try:
        logger.info("Triggering bulk all metrics analysis", limit=limit)
        
        # ) Build filters (same as get_auctions_report
        filters = {}
        if preferred is not None:
            filters['preferred'] = preferred
        if auction_site:
            filters['auction_site'] = auction_site
        if offering_type:
            filters['offering_type'] = offering_type.lower().strip()
        if tlds:
            filters['tlds'] = [t.strip() for t in tlds.split(',') if t.strip()]
        elif tld:
            filters['tld'] = tld
        if has_statistics is not None:
            filters['has_statistics'] = has_statistics
        if scored is not None:
            filters['scored'] = scored
        if min_rank is not None:
            filters['min_rank'] = min_rank
        if max_rank is not None:
            filters['max_rank'] = max_rank
        if min_score is not None:
            filters['min_score'] = min_score
        if max_score is not None:
            filters['max_score'] = max_score
        if expiration_from_date:
            filters['expiration_from_date'] = expiration_from_date
        if expiration_to_date:
            filters['expiration_to_date'] = expiration_to_date
        
        auctions_service = AuctionsService()
        
        # ) Get auctions matching filters (missing any metric OR force refresh
        auctions = await auctions_service.get_auctions_missing_any_metric_with_filters( filters=filters, sort_by=sort_by, sort_order=sort_order, limit=limit, force_refresh=force_refresh )
        
        if not auctions:
            return { "success": True, "message": "No domains matching filters and missing any DataForSEO metric found", "triggered_count": 0, "skipped_count": 0, "triggered_domains": [], "results": { "traffic_data": {"triggered": 0, "success": False}, "rank": {"triggered": 0, "success": False}, "backlinks": {"triggered": 0, "success": False}, "spam_score": {"triggered": 0, "success": False} } }
        
        domain_names = [a['domain'] for a in auctions]
        
        # --- Credit Deduction Logic ---
        db = get_database()
        pricing_service = PricingService()
        credits_service = CreditsService(db)
        
        # Calculate cost for syncing these domains
        total_cost = await pricing_service.calculate_action_cost('stats_sync', len(domain_names))
        
        logger.info("Deducting credits for bulk analysis", user_id=str(current_user.id), domain_count=len(domain_names), cost=total_cost)
        
        # Deduct credits
        success = await credits_service.deduct_credits( user_id=current_user.id, amount=total_cost, description=f"Bulk DataForSEO extraction for {len(domain_names)} domains", reference_id=f"bulk_sync_{int(datetime.now(timezone.utc).timestamp())}" )
        
        if not success:
            logger.warning("Insufficient credits for bulk analysis", user_id=str(current_user.id), cost=total_cost)
            raise HTTPException( status_code=402, detail=f"Insufficient credits. This action requires {total_cost} credits." )
        # ------------------------------
        
        # Trigger all four analyses sequentially
        # ) Trigger all four analyses in background to avoid API timeout (503
        n8n_service = N8NService()
        background_tasks.add_task( trigger_full_analysis_background, domain_names, n8n_service, str(current_user.id) )
        
        return { "success": True, "message": f"Successfully queued DataForSEO extraction for {len(domain_names)} domains. Metrics will update as they complete in the background and might take several minutes.", "triggered_count": len(domain_names), "skipped_count": 0, "triggered_domains": domain_names[:100] }
        
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to trigger bulk all metrics analysis", error=error_msg, limit=limit)
        
        # Check if it's a timeout or connection error
        if 'timeout' in error_msg.lower() or 'connection' in error_msg.lower() or 'reset' in error_msg.lower():
            raise HTTPException( status_code=504, detail=f"Database query timed out while fetching auctions. Error: {error_msg}" )
        
        raise HTTPException(status_code=500, detail=f"Failed to trigger bulk all metrics analysis: {error_msg}")


@router.get("/auctions/report")
async def get_auctions_report( search: Optional[str] = Query(None, description="Search by domain name"), preferred: Optional[bool] = Query(None, description="Filter by preferred status"), auction_site: Optional[str] = Query(None, description="Filter by auction site"), offering_type: Optional[str] = Query(None, description="Filter by market type: 'auction', 'backorder', 'buy_now'"), tld: Optional[str] = Query(None, description="Filter by TLD extension (e.g., '.com', '.ai') - deprecated, use tlds"), tlds: Optional[str] = Query(None, description="Comma-separated list of TLDs (e.g., '.com,.io,.ai')"), has_statistics: Optional[bool] = Query(None, description="Filter by has_statistics"), scored: Optional[bool] = Query(None, description="Filter by scored status (has score)"), min_rank: Optional[int] = Query(None, description="Minimum ranking", ge=1), max_rank: Optional[int] = Query(None, description="Maximum ranking", ge=1), min_score: Optional[float] = Query(None, description="Minimum score", ge=0, le=100), max_score: Optional[float] = Query(None, description="Maximum score", ge=0, le=100), expiration_from_date: Optional[str] = Query(None, description="Filter by expiration date from (YYYY-MM-DD)"), expiration_to_date: Optional[str] = Query(None, description="Filter by expiration date to (YYYY-MM-DD)"), auction_sites: Optional[str] = Query(None, description="Comma-separated list of auction sites (e.g., 'godaddy,namecheap')"), sort_by: str = Query("expiration_date", description="Field to sort by"), order: str = Query("asc", description="Sort order (asc, desc)"), limit: int = Query(50, description="Maximum number of records (reduced default to prevent timeouts)", ge=1, le=100), offset: int = Query(0, description="Number of records to skip", ge=0) ):
    """
    Get auctions report with page_statistics from auctions table
    
    Returns auctions with page_statistics when available. Records without statistics will have NULL page_statistics field. """
    try:
        # Build filters
        filters = {}
        if search:
            filters['search'] = search
        if preferred is not None:
            filters['preferred'] = preferred
        if auction_sites:
            # Handle "Go Daddy" vs "godaddy" by removing spaces and lowercasing
            filters['auction_sites'] = [s.strip().lower().replace(' ', '') for s in auction_sites.split(',') if s.strip()]
        if auction_site:
            filters['auction_site'] = auction_site
        if offering_type:
            # Normalize offering_type to lowercase for consistency
            filters['offering_type'] = offering_type.lower().strip()
            logger.info("Setting offering_type filter", offering_type=filters['offering_type'], original_value=offering_type)
            logger.debug("Setting offering_type filter", offering_type=offering_type, filter_dict=filters)
        if tlds:
            # Parse comma-separated TLDs into a list
            filters['tlds'] = [t.strip() for t in tlds.split(',') if t.strip()]
        elif tld:
            # Legacy single TLD support
            filters['tld'] = tld
        if has_statistics is not None:
            filters['has_statistics'] = has_statistics
        if scored is not None:
            filters['scored'] = scored
        if min_rank is not None:
            filters['min_rank'] = min_rank
        if max_rank is not None:
            filters['max_rank'] = max_rank
        if min_score is not None:
            filters['min_score'] = min_score
        if max_score is not None:
            filters['max_score'] = max_score
        
        if expiration_from_date:
            try:
                # Try simple format first
                # ) Check if it's already ISO format (contains T
                if 'T' in expiration_from_date:
                    # Validate it's parseable
                    datetime.fromisoformat(expiration_from_date.replace('Z', '+00:00'))
                    filters['expiration_from_date'] = expiration_from_date
                else:
                    # Assume YYYY-MM-DD, convert to ISO start of day in UTC
                    dt = datetime.strptime(expiration_from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    filters['expiration_from_date'] = dt.isoformat().replace('+00:00', 'Z')
            except ValueError:
                logger.warning("Invalid expiration_from_date format, defaulting to NOW", date=expiration_from_date)
                filters['expiration_from_date'] = datetime.now(timezone.utc).isoformat()
        
        if expiration_to_date:
            filters['expiration_to_date'] = expiration_to_date
        
        logger.info("Fetching auctions report", filters=filters, limit=limit, offset=offset)

        auctions_service = AuctionsService()
        result = await auctions_service.get_auctions_report( filters=filters, sort_by=sort_by, order=order, limit=limit, offset=offset )
        
        count = result.get("count", 0)
        total_count = result.get("total_count", 0)
        logger.info("Auctions report result", count=count, total=total_count, has_more=result.get("has_more", False))
        
        return { "success": True, "count": count, "total_count": total_count, "has_more": result.get("has_more", False), "auctions": result.get("auctions", []) }
        
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        logger.error("Failed to get auctions report", error=error_msg, error_type=error_type, sort_by=sort_by, order=order, limit=limit, offset=offset, exc_info=True)
        
        # Check if it's a timeout or connection error
        if 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower():
            raise HTTPException( status_code=504, detail=f"Database query timed out. {error_msg}" )
        elif 'connection' in error_msg.lower() or 'reset' in error_msg.lower() or 'no available server' in error_msg.lower():
            raise HTTPException( status_code=503, detail=f"Database connection error. {error_msg}" )
        elif 'not found' in error_msg.lower() or 'does not exist' in error_msg.lower() or '42703' in error_msg:
            # Only return 404 for actual missing resources, not for RPC function errors
            if 'rpc' in error_msg.lower() or 'function' in error_msg.lower() or '42703' in error_msg:
                # Log full error for debugging
                logger.error("Database function error", error=error_msg, error_type=type(e).__name__, exc_info=True)
                # Extract full error details
                full_error = error_msg
                if hasattr(e, 'args') and e.args:
                    if isinstance(e.args[0], dict):
                        full_error = str(e.args[0])
                    elif isinstance(e.args[0], str):
                        full_error = e.args[0]
                raise HTTPException( status_code=500, detail=f"Database function error (code 42703 = undefined column). The filter_auctions_by_tlds function may have a missing column. Please ensure migration 20250131000013_fix_tld_filter_function.sql is applied. Full error: {full_error}" )
            raise HTTPException( status_code=404, detail=f"Database table or resource not found. {error_msg}" )
        
        raise HTTPException(status_code=500, detail=f"Failed to retrieve auctions report: {error_msg}")


@router.post("/auctions/process-scoring-batch")
async def process_scoring_batch( batch_size: int = Query(10000, ge=1, le=50000, description="Number of records to process"), config_id: Optional[str] = Query(None, description="Optional scoring config ID"), recalculate_rankings: bool = Query(True, description="Recalculate global rankings after processing") ):
    """
    Process a batch of unprocessed auctions through the scoring pipeline. This endpoint:
    1. Fetches unprocessed records with pre-scoring from Supabase
    2. Calculates complex scores (LFS, semantic) in Python
    3. Updates scores back to database
    4. Optionally recalculates global rankings
    
    Returns processing statistics. """
    try:
        scoring_service = AuctionScoringService()
        result = await scoring_service.process_batch( batch_size=batch_size, config_id=config_id, recalculate_rankings_after=recalculate_rankings )
        return result
    except Exception as e:
        logger.error("Failed to process scoring batch", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auctions/scoring-stats")
async def get_scoring_stats():
    """
    Get statistics about auction scoring progress. Returns counts of processed, unprocessed, and scored records. """
    try:
        scoring_service = AuctionScoringService()
        stats = await scoring_service.get_processing_stats()
        return stats
    except Exception as e:
        logger.error("Failed to get scoring stats", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auctions/recalculate-rankings")
async def recalculate_rankings():
    """
    Recalculate global rankings and preferred flags for all scored auctions. This should be called periodically or after processing large batches. """
    try:
        scoring_service = AuctionScoringService()
        result = await scoring_service.recalculate_rankings()
        return result
    except Exception as e:
        logger.error("Failed to recalculate rankings", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auctions/tlds")
async def get_unique_tlds():
    """
    Get all unique TLD extensions from the auctions table
    
    Returns a list of unique TLDs (e.g., ['.com', '.ai', '.net'])
    """
    try:
        db = get_database()
        tlds = await db.get_unique_tlds()
        return {"tlds": tlds}
    except Exception as e:
        logger.error("Failed to get unique TLDs", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve TLDs: {str(e)}")


@router.post("/auctions/{domain}/wayback-first-seen")
async def fetch_wayback_first_seen(domain: str):
    """
    Fetch first seen date from Wayback Machine for a domain and update the auction record
    
    Returns the first seen date if found, or None if not found
    """
    try:
        wayback_service = WaybackMachineService()
        db = get_database()
        
        # Fetch Wayback Machine data with timeout handling
        try:
            wayback_data = asyncio.wait_for( wayback_service.get_domain_history(domain), timeout=30.0 ) # 30 second timeout
        except asyncio.TimeoutError:
            logger.warning("Wayback Machine request timed out", domain=domain)
            return { "success": False, "message": "Request timed out. Wayback Machine may be slow or unavailable.", "first_seen": None }
        except Exception as e:
            logger.error("Wayback Machine request failed", domain=domain, error=str(e))
            return { "success": False, "message": f"Failed to fetch from Wayback Machine: {str(e)}", "first_seen": None }
        
        if not wayback_data:
            logger.info("No Wayback Machine data returned", domain=domain)
            return { "success": False, "message": "No Wayback Machine data found for this domain", "first_seen": None }
        
        # Get the first capture timestamp
        captures = wayback_data.get('captures', [])
        if not captures:
            logger.info("No captures found in Wayback Machine data", domain=domain)
            return { "success": False, "message": "No captures found for this domain", "first_seen": None }
        
        # Find the earliest capture
        try:
            first_capture = min(captures, key=lambda x: x.get("timestamp", "99999999999999"))
            first_timestamp = first_capture.get("timestamp")
        except Exception as e:
            logger.error("Failed to find earliest capture", domain=domain, error=str(e))
            return { "success": False, "message": "Failed to process capture data", "first_seen": None }
        
        if not first_timestamp:
            return { "success": False, "message": "Invalid timestamp in capture data", "first_seen": None }
        
        # ) Parse timestamp (format: YYYYMMDDHHMMSS
        try:
            first_seen_dt = datetime.strptime(first_timestamp, "%Y%m%d%H%M%S")
        except ValueError:
            # Try with just date part
            try:
                first_seen_dt = datetime.strptime(first_timestamp[:8], "%Y%m%d")
            except ValueError:
                logger.error("Failed to parse timestamp", domain=domain, timestamp=first_timestamp)
                return { "success": False, "message": "Failed to parse timestamp", "first_seen": None }
        
        # Update all auction records for this domain with the first_seen date
        if not db.client:
            raise HTTPException(status_code=503, detail="Database connection not available")
        
        try:
            result = (await db._get_client()).table('auctions').update({ 'first_seen': first_seen_dt.isoformat() }).eq('domain', domain).execute()
            
            updated_count = len(result.data) if result.data else 0
            
            logger.info("Updated first_seen from Wayback Machine", domain=domain, first_seen=first_seen_dt.isoformat(), updated_count=updated_count)
            
            return { "success": True, "first_seen": first_seen_dt.isoformat(), "first_seen_year": first_seen_dt.year, "updated_count": updated_count }
        except Exception as e:
            logger.error("Failed to update database", domain=domain, error=str(e))
            return { "success": False, "message": f"Failed to update database: {str(e)}", "first_seen": None }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to fetch Wayback Machine first seen", domain=domain, error=error_msg, exc_info=True)
        return { "success": False, "message": f"Unexpected error: {error_msg}", "first_seen": None }


async def get_queue_count() -> int:
    """Get count of pending items in queue"""
    db = get_database()
    if not db.client:
        return 0
    try:
        return await db.get_queue_count()
    except Exception as e:
        logger.error("Failed to get queue count", error=str(e))
        return 0


async def process_dataforseo_queue():
    """
    Process the DataForSEO queue when it reaches 100 domains
    Gets top 100 domains ordered by expiration_date (closest to NOW first)
    """
    try:
        db = get_database()
        if not db.client:
            logger.error("Database connection not available for queue processing")
            return
        
        # Get 100 pending domains ordered by expiration_date ASC (closest to NOW first)
        queue_result = await (await db._get_client()).table('dataforseo_queue').select( 'id,domain,expiration_date' ).eq('status', 'pending').order('expiration_date', desc= False).limit(100).execute()
        
        if not queue_result.data or len(queue_result.data) < 100:
            logger.info("Queue does not have 100 domains yet", count=len(queue_result.data) if queue_result.data else 0)
            return
        
        domains = [item['domain'] for item in queue_result.data]
        queue_ids = [item['id'] for item in queue_result.data]
        
        # Update queue items to 'processing'
        await (await db._get_client()).table('dataforseo_queue').update({ 'status': 'processing', 'updated_at': datetime.now(timezone.utc).isoformat() }).in_('id', queue_ids).execute()
        
        logger.info("Processing DataForSEO queue", domain_count=len(domains))
        
        # Trigger DataForSEO analysis via N8N
        n8n_service = N8NService()
        n8n_result = await n8n_service.trigger_bulk_page_summary_workflow(domains)
        
        if n8n_result:
            logger.info("Triggered N8N workflow for queued domains", domain_count=len(domains), request_id=n8n_result.get('request_id'))
            # Note: Queue items will be marked as 'completed' by the n8n webhook callback
            # when page_statistics are updated in the auctions table
        else:
            # Mark as failed if N8N trigger failed
            await (await db._get_client()).table('dataforseo_queue').update({ 'status': 'failed', 'error_message': 'Failed to trigger N8N workflow', 'updated_at': datetime.now(timezone.utc).isoformat() }).in_('id', queue_ids).execute()
            logger.error("Failed to trigger N8N workflow for queue", queue_ids=queue_ids)
            
    except Exception as e:
        logger.error("Failed to process DataForSEO queue", error=str(e), exc_info=True)


@router.post("/auctions/{domain}/queue-dataforseo")
async def queue_domain_for_dataforseo(domain: str):
    """
    Add a domain to the DataForSEO queue for on-demand analysis
    
    Requirements:
    - Domain must exist in auctions table
    - Domain must have score > 0 (scored)
    - Domain must not have page_statistics (not already analyzed)
    - Domain must not already be in queue
    
    Returns queue position and current queue count
    """
    try:
        db = get_database()
        if not db.client:
            raise HTTPException(status_code=503, detail="Database connection not available")
        
        # Check if domain exists in auctions table and meets criteria
        auction_result = await (await db._get_client()).table('auctions').select( 'id,domain,score,expiration_date,page_statistics' ).eq('domain', domain).limit(1).execute()
        
        if not auction_result.data or len(auction_result.data) == 0:
            return { "success": False, "message": "Domain not found in auctions table", "queued": False }
        
        auction = auction_result.data[0]
        
        # ) Check if domain is scored (score > 0
        if not auction.get('score') or auction['score'] <= 0:
            return { "success": False, "message": "Domain must be scored (score > 0) to queue for DataForSEO analysis", "queued": False }
        
        # Check if domain already has page_statistics
        if auction.get('page_statistics'):
            return { "success": False, "message": "Domain already has DataForSEO data", "queued": False }
        
        # Check if domain is already in queue
        queue_check = await (await db._get_client()).table('dataforseo_queue').select('id,status').eq('domain', domain).limit(1).execute()
        if queue_check.data and len(queue_check.data) > 0:
            queue_item = queue_check.data[0]
            if queue_item['status'] == 'pending':
                # Get position in queue
                position_result = await (await db._get_client()).table('dataforseo_queue').select('id').eq('status', 'pending').order('expiration_date', desc=False).execute()
                position = None
                if position_result.data:
                    for idx, item in enumerate(position_result.data, 1):
                        if item['id'] == queue_item['id']:
                            position = idx
                            break
                
                queue_count = await get_queue_count()
                return { "success": True, "message": "Domain already in queue", "queued": True, "position": position, "queue_count": queue_count }
        
        # Add to queue
        queue_data = { 'domain': domain, 'status': 'pending', 'expiration_date': auction.get('expiration_date'), 'score': auction.get('score'), 'auction_id': auction.get('id') }
        
        result = await (await db._get_client()).table('dataforseo_queue').insert(queue_data).execute()
        
        # Get queue count
        queue_count = await get_queue_count()
        
        # Check if we've reached 100 and trigger processing
        if queue_count >= 100:
            # Trigger processing in background
            asyncio.create_task(process_dataforseo_queue())
        
        # ) Get position in queue (ordered by expiration_date ASC
        position_result = await (await db._get_client()).table('dataforseo_queue').select('id').eq('status', 'pending').order('expiration_date', desc=False).execute()
        position = None
        if position_result.data:
            for idx, item in enumerate(position_result.data, 1):
                if item['id'] == result.data[0]['id']:
                    position = idx
                    break
        
        logger.info("Domain added to DataForSEO queue", domain=domain, position=position, queue_count=queue_count)
        
        return { "success": True, "message": "Domain added to queue", "queued": True, "position": position, "queue_count": queue_count, "will_process": queue_count >= 100 }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to queue domain for DataForSEO", domain=domain, error=error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to queue domain: {error_msg}")


@router.get("/auctions/dataforseo-queue/status")
async def get_dataforseo_queue_status(domain: Optional[str] = Query(None, description="Domain to check position for")):
    """
    Get DataForSEO queue status
    
    Returns:
    - Total queue count
    - User's domain position if domain is provided
    """
    try:
        db = get_database()
        if not db.client:
            raise HTTPException(status_code=503, detail="Database connection not available")
        
        # Get queue count
        queue_count = get_queue_count()
        
        result = { "queue_count": queue_count, "max_queue_size": 100, "ready_to_process": queue_count >= 100 }
        
        # If domain provided, check position
        if domain:
            queue_item = (await db._get_client()).table('dataforseo_queue').select('id,status').eq('domain', domain).eq('status', 'pending').limit(1).execute()
            if queue_item.data and len(queue_item.data) > 0:
                # Calculate position
                position_result = (await db._get_client()).table('dataforseo_queue').select('id').eq('status', 'pending').order('expiration_date', desc=False).execute()
                position = None
                if position_result.data:
                    for idx, item in enumerate(position_result.data, 1):
                        if item['id'] == queue_item.data[0]['id']:
                            position = idx
                            break
                result["domain_queued"] = True
                result["position"] = position
            else:
                result["domain_queued"] = False
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to get queue status", error=error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get queue status: {error_msg}")


@router.delete("/auctions/{domain}/queue-dataforseo")
async def cancel_domain_queue_request(domain: str):
    """
    Remove a domain from the DataForSEO queue (cancel queue request)
    
    Only removes domains with 'pending' status. Domains that are already 'processing'
    cannot be cancelled. Returns success status
    """
    try:
        db = get_database()
        if not db.client:
            raise HTTPException(status_code=503, detail="Database connection not available")
        
        # Check if domain is in queue
        queue_check = (await db._get_client()).table('dataforseo_queue').select('id,status').eq('domain', domain).limit(1).execute()
        
        if not queue_check.data or len(queue_check.data) == 0:
            return { "success": False, "message": "Domain not found in queue", "cancelled": False }
        
        queue_item = queue_check.data[0]
        
        # Only allow cancelling pending items
        if queue_item['status'] != 'pending':
            return { "success": False, "message": f"Cannot cancel domain with status '{queue_item['status']}'. Only pending requests can be cancelled.", "cancelled": False }
        
        # Delete from queue
        result = (await db._get_client()).table('dataforseo_queue').delete().eq('id', queue_item['id']).execute()
        
        logger.info("Domain removed from DataForSEO queue", domain=domain)
        
        return { "success": True, "message": "Domain removed from queue", "cancelled": True }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to cancel queue request", domain=domain, error=error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cancel queue request: {error_msg}")


@router.post("/auctions/delete-expired")
async def delete_expired_auctions():
    """
    Manually delete all expired auctions (expiration_date < NOW())
    This endpoint can be called to clean up expired records at any time. Returns:
        Number of records deleted
    """
    try:
        db = get_database()
        deleted_count = await db.delete_expired_auctions()
        
        return { "success": True, "message": f"Deleted {deleted_count} expired auction(s)", "deleted_count": deleted_count }
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to delete expired auctions", error=error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete expired auctions: {error_msg}")


@router.get("/auctions/refresh-costs")
async def get_refresh_costs(current_user = Depends(get_current_user)):
    """Get the credit costs for various refresh actions"""
    try:
        from services.marketplace_batch_service import MarketplaceBatchService
        service = MarketplaceBatchService()
        costs = service.get_refresh_costs()
        return costs
    except Exception as e:
        logger.error("Failed to get refresh costs", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auctions/refresh-preview")
async def get_refresh_preview( payload: Dict[str, Any] = Body(...), current_user = Depends(get_current_user) ):
    """
    Preview how many domains would be refreshed with the given filters. Body: { filters: {...}, force: bool }

    Returns: { domain_count: int, would_refresh: bool, filters: {...} }
    """
    try:
        from services.auctions_service import AuctionsService
        service = AuctionsService()

        filters = payload.get("filters", payload)
        force = payload.get("force", False)
        sort_by = payload.get("sort_by", "expiration_date")
        sort_order = payload.get("sort_order", "asc")

        domains_data = await service.get_auctions_missing_any_metric_with_filters( filters=filters, sort_by=sort_by, sort_order=sort_order, limit=1000, force_refresh=force )

        return { "success": True, "domain_count": len(domains_data), "would_refresh": len(domains_data) > 0, "filters": filters, "force": force, "message": f"Found {len(domains_data)} domains that would be refreshed" if domains_data else "No domains need refreshing - all have fresh metrics" }
    except Exception as e:
        logger.error("Failed to get refresh preview", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auctions/bulk-refresh")
async def trigger_bulk_refresh( payload: Dict[str, Any] = Body(...), background_tasks: BackgroundTasks = BackgroundTasks(), current_user = Depends(get_current_user) ):
    """
    'Find and Fill' — refresh up to 1,000 domains with missing metrics.
    Body: { filters: {...}, force: bool, prioritized_domains: [...] }

    prioritized_domains: Optional list of domains to prioritize for refresh.
    These will be processed first, then remaining slots filled with other domains matching filters.

    Returns immediately with 'in_progress' status; processing continues in background. """
    try:
        from services.marketplace_batch_service import MarketplaceBatchService
        from services.progress_tracker import ProgressTracker
        service = MarketplaceBatchService()

        # The Angular client wraps filters in { filters: {...}, force: bool, ... }
        filters = payload.get("filters", payload)  # Fallback: treat whole body as filters
        force = payload.get("force", False)
        sort_by = payload.get("sort_by", "expiration_date")
        sort_order = payload.get("sort_order", "asc")
        prioritized_domains = payload.get("prioritized_domains", [])  # New parameter

        # Extract user ID before passing to background task
        user_id = current_user.id

        # Determine if we should only refresh displayed domains (prioritized_domains only)
        # If user sends only_displayed=true, we'll only refresh those domains
        only_displayed = payload.get("only_displayed", False)

        # Calculate estimated total - if only_displayed, use prioritized count, otherwise up to 1000
        estimated_total = len(prioritized_domains) if only_displayed and prioritized_domains else 1000

        # Create a progress job (will be updated once domains are found)
        job_id = await ProgressTracker.create_job( user_id=str(user_id), job_type="bulk_refresh", total_items=estimated_total,
            metadata={"filters": filters, "force": False, "prioritized_count": len(prioritized_domains) if prioritized_domains else 0, "only_displayed": only_displayed} )

        # Start processing in background and return immediately
        background_tasks.add_task( service.process_marketplace_refresh, user_id=user_id, filters=filters, force=False,
            job_id=job_id, sort_by=sort_by, sort_order=sort_order, prioritized_domains=prioritized_domains,
            only_displayed=only_displayed )

        if only_displayed and prioritized_domains:
            return { "success": True, "in_progress": True, "job_id": job_id,
                "message": f"Fill Gaps refresh started — processing {len(prioritized_domains)} displayed domains only." }
        return { "success": True, "in_progress": True, "job_id": job_id,
            "message": f"Fill Gaps refresh started — processing up to 1,000 domains in the background ({len(prioritized_domains) if prioritized_domains else 0} prioritized)." }
    except Exception as e:
        logger.error("Failed to trigger bulk refresh", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auctions/force-refresh")
async def trigger_force_refresh( payload: Dict[str, Any] = Body(...), background_tasks: BackgroundTasks = BackgroundTasks(), current_user = Depends(get_current_user) ):
    """
    Force Refresh — get fresh SEO metrics for up to 1,000 domains matching filters, overriding any existing metrics regardless of when they were last refreshed.
    Body: { filters: {...}, force: bool, prioritized_domains: [...] }

    prioritized_domains: Optional list of domains to prioritize for refresh.

    Returns immediately with 'in_progress' status; processing continues in background. """
    try:
        from services.marketplace_batch_service import MarketplaceBatchService
        from services.progress_tracker import ProgressTracker
        service = MarketplaceBatchService()

        # Same payload format as bulk-refresh
        filters = payload.get("filters", payload)
        sort_by = payload.get("sort_by", "expiration_date")
        sort_order = payload.get("sort_order", "asc")
        prioritized_domains = payload.get("prioritized_domains", [])
        only_displayed = payload.get("only_displayed", False)

        # Extract user ID before passing to background task
        user_id = current_user.id

        # Create a progress job (will be updated once domains are found)
        job_id = await ProgressTracker.create_job( user_id=str(user_id), job_type="force_refresh", total_items=1000,
            metadata={"filters": filters, "force": True, "prioritized_count": len(prioritized_domains), "only_displayed": only_displayed} )

        # Start processing in background and return immediately
        background_tasks.add_task( service.process_marketplace_refresh, user_id=user_id, filters=filters, force=True,
            job_id=job_id, sort_by=sort_by, sort_order=sort_order, prioritized_domains=prioritized_domains, only_displayed=only_displayed )

        return { "success": True, "in_progress": True, "job_id": job_id,
            "message": f"Force Refresh started — processing up to 1,000 domains in the background ({len(prioritized_domains)} prioritized)." }
    except Exception as e:
        logger.error("Failed to trigger force refresh", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auctions/refresh-status/{job_id}")
async def get_refresh_status( job_id: str, current_user = Depends(get_current_user) ):
    """
    Get the status of a running refresh job. Returns progress information including percent complete and current status. """
    try:
        from services.progress_tracker import ProgressTracker

        status = await ProgressTracker.get_job_status(job_id)

        if not status:
            raise HTTPException(status_code=404, detail="Job not found or expired")

        # Verify user owns this job
        if status.get("user_id") != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to view this job")

        return { "success": True, "job_id": job_id, "status": status.get("status"), "progress_percent": status.get("progress_percent", 0), "total_items": status.get("total_items", 0), "processed_items": status.get("processed_items", 0), "failed_items": status.get("failed_items", 0), "current_batch": status.get("current_batch", 0), "total_batches": status.get("total_batches", 0), "message": status.get("message", ""), "started_at": status.get("started_at"), "completed_at": status.get("completed_at") }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get refresh status", error=str(e), job_id=job_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auctions/refresh-history")
async def get_refresh_history( limit: int = Query(20, ge=1, le=100), current_user = Depends(get_current_user) ):
    """Get the batch refresh history for the current user"""
    try:
        from services.marketplace_batch_service import MarketplaceBatchService
        service = MarketplaceBatchService()
        history = service.get_refresh_history(user_id=current_user.id, limit=limit)
        return history
    except Exception as e:
        logger.error("Failed to get refresh history", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auctions/domain-refresh")
async def trigger_domain_refresh( payload: Dict[str, Any] = Body(...), current_user = Depends(get_current_user) ):
    """Trigger a refresh for a single domain"""
    try:
        domain = payload.get("domain")
        if not domain:
            raise HTTPException(status_code=400, detail="Domain is required")
            
        from services.marketplace_batch_service import MarketplaceBatchService
        service = MarketplaceBatchService()
        result = service.refresh_single_domain( user_id=current_user.id, domain=domain )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to trigger domain refresh", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auctions/{auction_id}/preferred")
async def toggle_preferred_auction( auction_id: str, payload: Dict[str, Any] = Body(...), db = Depends(get_database), current_user = Depends(get_current_user) ):
    """Toggle the preferred status of an auction"""
    try:
        preferred = payload.get("preferred", False)
        
        # We don't check for ownership here since auctions are shared across users in the base table. # But this flag affects how they are filtered/shown. # In this system, 'preferred' is usually global or we'd need a sub-table per user. # Given the current schema, we update the auctions table. # DO NOT update `updated_at` here, because `updated_at` is used by the frontend
        # to determine if SEO metrics are "fresh" or "stale". Toggling a favorite 
        # is just a UI metadata change and should not trigger a "fresh" state.
        client = await db._get_client()
        result = await client.table('auctions').update({ 'preferred': preferred }).eq('id', auction_id).execute()
        
        if not result.data:
            # ) If no auction with that ID, it might be a UUID mismatch or domain-based update needed. # But normally auctions have a UUID ID. logger.warning("No auction found to toggle preferred", auction_id=auction_id
            return {"success": False, "message": "Auction not found"}
            
        return {"success": True, "preferred": preferred}
        
    except Exception as e:
        logger.error("Failed to toggle preferred auction", auction_id=auction_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
