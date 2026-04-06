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

# Single staging table for optimized import
STAGING_TABLE = 'auctions_import'


async def _clear_staging_for_batch(db, import_batch_id: str):
    """
    Clear staging table for a specific import batch.
    Called before new import to ensure clean slate.
    """
    logger.info("Clearing staging table for batch", import_batch_id=import_batch_id)
    client = await db._get_client()

    try:
        await client.table(STAGING_TABLE).delete().eq('import_batch_id', import_batch_id).execute()
        logger.info("Staging table cleared", import_batch_id=import_batch_id)
    except Exception as e:
        logger.warning("Failed to clear staging table (might be empty)", import_batch_id=import_batch_id, error=str(e))


async def _insert_to_staging(db, records: List[Dict], import_batch_id: str, batch_size: int = 5000) -> int:
    """
    Bulk insert records to staging table in batches.
    Optimized for large imports (5,000-10,000 domains/sec).
    Handles duplicate domains within the same batch by using upsert.
    """
    if not records:
        return 0

    client = await db._get_client()
    total_inserted = 0

    # Add import_batch_id to all records
    for record in records:
        record['import_batch_id'] = import_batch_id

    # Deduplicate within the batch - keep last occurrence
    seen = {}
    for record in records:
        key = (record.get('domain'), record.get('auction_site'))
        seen[key] = record
    deduped_records = list(seen.values())

    if len(deduped_records) < len(records):
        logger.info("Deduplicated records in batch",
                    original=len(records),
                    deduplicated=len(deduped_records))

    # Insert in batches using upsert to handle any remaining conflicts
    for i in range(0, len(deduped_records), batch_size):
        batch = deduped_records[i:i + batch_size]

        for attempt in range(3):
            try:
                # Use upsert with on_conflict to handle duplicates gracefully
                await client.table(STAGING_TABLE).upsert(
                    batch,
                    on_conflict='import_batch_id,domain,auction_site'
                ).execute()
                total_inserted += len(batch)
                break
            except Exception as e:
                if attempt == 2:
                    logger.error("Failed to insert batch to staging", attempt=attempt, error=str(e))
                    raise
                await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff

        # Brief yield to event loop
        if i + batch_size < len(deduped_records):
            await asyncio.sleep(0.001)

    return total_inserted


async def _perform_atomic_import(db, auction_site: str, import_batch_id: str, offering_type: str = None, cleanup_stale: bool = False) -> Dict:
    """
    Perform atomic import: UPSERT new, UPDATE existing.
    Cleanup (DELETE) stale records only if cleanup_stale is True (usually on final chunk).
    """
    logger.info("Starting atomic import", import_batch_id=import_batch_id, auction_site=auction_site, cleanup_stale=cleanup_stale)

    client = await db._get_client()

    try:
        result = await client.rpc('import_auctions_batch', {
            'p_import_batch_id': import_batch_id,
            'p_auction_site': auction_site,
            'p_offering_type': offering_type,
            'p_cleanup_stale': cleanup_stale
        }).execute()

        if result.data:
            import_result = result.data[0] if isinstance(result.data, list) else result.data
            logger.info("Atomic import complete",
                       import_batch_id=import_batch_id,
                       inserted=import_result.get('inserted'),
                       updated=import_result.get('updated'),
                       deleted=import_result.get('deleted'),
                       new_domains=import_result.get('new_domains'))
            return import_result

        return {'success': False, 'error': 'No result from import function'}

    except Exception as e:
        logger.error("Atomic import failed", import_batch_id=import_batch_id, error=str(e))
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

        # 2. Staging count (new table)
        staging_count_res = await client.table('auctions_import').select('count', count='exact').limit(1).execute()

        # 3. Storage buckets
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


async def _score_new_domains_after_import(db, import_batch_id: str, scoring_service, fast_mode: bool = False) -> int:
    """
    Score only NEW domains that were just inserted (score is NULL).
    Uses the database function to find new domains efficiently.
    """
    logger.info("Starting post-import scoring", import_batch_id=import_batch_id, fast_mode=fast_mode)

    client = await db._get_client()
    total_scored = 0
    batch_size = 5000
    UPSERT_BATCH_SIZE = 1000

    try:
        from services.csv_parser_service import CSVParserService
        parser = CSVParserService()
        
        while True:
            # Get batch of new domains from this import
            result = await client.rpc('get_new_domains_for_scoring', {
                'p_import_batch_id': import_batch_id,
                'p_limit': batch_size
            }).execute()

            if not result.data or len(result.data) == 0:
                break

            new_domains = result.data
            batch_updates = []

            # Prepare records
            for domain_record in new_domains:
                try:
                    # Parse domain to get scoring data
                    parsed = parser.parse_single_domain(domain_record['domain'])
                    if parsed and hasattr(parsed, 'total_meaning_score') and parsed.total_meaning_score is not None:
                        score = float(parsed.total_meaning_score)
                    else:
                        score = 0.0

                    # MUST include unique constraint columns: domain, auction_site, expiration_date
                    batch_updates.append({
                        'domain': domain_record['domain'],
                        'auction_site': domain_record['auction_site'],
                        'expiration_date': domain_record['expiration_date'],
                        'score': score,
                        'processed': True,
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    })

                except Exception as e:
                    logger.warning("Failed to score domain", domain=domain_record.get('domain'), error=str(e))
                    batch_updates.append({
                        'domain': domain_record['domain'],
                        'auction_site': domain_record['auction_site'],
                        'expiration_date': domain_record['expiration_date'],
                        'score': 0.0,
                        'processed': True
                    })

            # Perform BATCH UPSERT in smaller chunks
            scored_count = 0
            for i in range(0, len(batch_updates), UPSERT_BATCH_SIZE):
                sub_batch = batch_updates[i:i + UPSERT_BATCH_SIZE]
                try:
                    # Use UPSERT to update existing records based on unique constraint
                    await client.table('auctions').upsert(
                        sub_batch,
                        on_conflict='domain,auction_site'
                    ).execute()
                    scored_count += len(sub_batch)
                except Exception as e:
                    logger.warning(f"Batch upsert failed for sub-batch {i}, falling back to individual updates", error=str(e))
                    for sd in sub_batch:
                        try:
                            query = client.table('auctions').update({
                                'score': sd['score'],
                                'processed': True
                            }).eq('domain', sd['domain']).eq('auction_site', sd['auction_site'])
                            
                            if sd['expiration_date'] is not None:
                                query = query.eq('expiration_date', sd['expiration_date'])
                            else:
                                query = query.is_('expiration_date', 'null')
                                
                            await query.execute()
                            scored_count += 1
                        except Exception:
                            pass

            total_scored += scored_count
            logger.info("Scored batch", import_batch_id=import_batch_id, batch_scored=scored_count, total_scored=total_scored)

            # Update progress periodically in the database
            try:
                await db.update_csv_upload_progress(
                    job_id=import_batch_id,
                    status='processing',
                    current_stage='scoring',
                    processed_records=total_scored
                )
            except Exception as e:
                logger.warning("Failed to update progress in DB", error=str(e))

            # Yield control
            await asyncio.sleep(0.01)

        logger.info("Post-import scoring complete", import_batch_id=import_batch_id, total_scored=total_scored)
        return total_scored

    except Exception as e:
        logger.error("Post-import scoring failed", import_batch_id=import_batch_id, error=str(e))
        return total_scored


async def _score_new_domains_after_merge(db, auction_site: str, scoring_service, job_id: str, fast_mode: bool = False) -> int:
    """
    Score only NEW domains that were just inserted (score is NULL).
    Existing domains kept their previous score.

    OPTIMIZED: Uses batch SELECT and batch UPSERT to minimize network latency.
    """
    logger.info("Starting post-merge scoring for new domains", job_id=job_id, auction_site=auction_site, fast_mode=fast_mode)

    total_scored = 0
    BATCH_SIZE = 500  # Fetch more records per batch
    UPSERT_BATCH_SIZE = 100  # Upsert in chunks to avoid request size limits

    while True:
        # Fetch unprocessed/new domains (score is NULL)
        try:
            result = await (await db._get_client()).table('auctions').select(
                'domain', 'expiration_date', 'start_date', 'offer_type'
            ).eq('auction_site', auction_site).is_('score', None).limit(BATCH_SIZE).execute()
        except Exception as e:
            logger.error("Failed to fetch domains for scoring", error=str(e))
            break

        if not result.data:
            break

        domains_to_score = result.data
        logger.info(f"Scoring batch of {len(domains_to_score)} domains (Total so far: {total_scored})", job_id=job_id)

        # Score all domains in the batch
        batch_updates = []
        for record in domains_to_score:
            try:
                # Create NamecheapDomain for scoring service
                namecheap_domain = NamecheapDomain(
                    name=record['domain'],
                    registered_date=None,
                    url=None,
                    start_date=record.get('start_date'),
                    end_date=record.get('expiration_date'),
                    price=None
                )

                # Score the domain (using fast_mode if enabled)
                scored = scoring_service.score_domain(namecheap_domain, fast_mode=fast_mode)
                score_value = scored.total_meaning_score if scored.total_meaning_score is not None else 0.0

                # Prepare upsert record
                # MUST include unique constraint columns: domain, auction_site, expiration_date
                batch_updates.append({
                    'domain': record['domain'],
                    'auction_site': auction_site,
                    'expiration_date': record['expiration_date'],
                    'score': score_value,
                    'processed': True,
                    'updated_at': datetime.now().isoformat()
                })

            except Exception as e:
                logger.warning(f"Failed to score domain {record.get('domain')}", error=str(e))
                # Still add to batch with 0 score to mark as processed
                batch_updates.append({
                    'domain': record['domain'],
                    'auction_site': auction_site,
                    'expiration_date': record['expiration_date'],
                    'score': 0.0,
                    'processed': True
                })

        # Perform BATCH UPSERT in smaller chunks
        for i in range(0, len(batch_updates), UPSERT_BATCH_SIZE):
            sub_batch = batch_updates[i:i + UPSERT_BATCH_SIZE]
            try:
                # Use UPSERT to update existing records based on unique constraint
                await (await db._get_client()).table('auctions').upsert(
                    sub_batch,
                    on_conflict='domain,auction_site,expiration_date'
                ).execute()
                total_scored += len(sub_batch)
            except Exception as e:
                logger.warning(f"Batch upsert failed for sub-batch {i}, falling back to individual updates", error=str(e))
                # Fallback to individual updates if something is wrong with the batch
                for sd in sub_batch:
                    try:
                        await (await db._get_client()).table('auctions').update({
                            'score': sd['score'],
                            'processed': True
                        }).eq('domain', sd['domain']).eq('auction_site', auction_site).eq('expiration_date', sd['expiration_date']).execute()
                        total_scored += 1
                    except Exception:
                        pass

        # Update progress periodically in the database
        try:
            await db.update_csv_upload_progress(
                job_id=job_id,
                status='processing',
                current_stage='scoring_new',
                processed_records=total_scored
            )
        except Exception as e:
            logger.warning("Failed to update progress in DB", error=str(e))

        # Small yield to event loop
        await asyncio.sleep(0.1)

    logger.info("Post-merge scoring complete", job_id=job_id, auction_site=auction_site, total_scored=total_scored)
    
    # Final progress update
    try:
        await db.update_csv_upload_progress(
            job_id=job_id,
            status='completed',
            current_stage='finished',
            progress_percentage='100.00',
            completed_at=datetime.now().isoformat()
        )
    except Exception:
        pass
        
    return total_scored


async def process_csv_upload_async( job_id: str, csv_content: str, filename: str, auction_site: str, offering_type: Optional[str] = None, is_file: bool = False ):
    """
    Optimized CSV upload processing using single staging table and atomic import.

    Args:
        job_id: Unique job identifier (also used as import_batch_id)
        csv_content: CSV file content as string OR file path if is_file=True
        filename: Original filename
        auction_site: Auction site source
        is_file: Whether csv_content is a file path

    Performance: 5000-10000 domains/sec (single transaction atomic import)
    """
    import psutil
    import os

    try:
        process = psutil.Process(os.getpid())
        start_mem = process.memory_info().rss / 1024 / 1024
        logger.info(f"[CSV UPLOAD START] {job_id}", filename=filename, auction_site=auction_site, start_memory_mb=start_mem, offering_type=offering_type)
    except ImportError:
        logger.info(f"[CSV UPLOAD START] {job_id}", filename=filename, auction_site=auction_site, offering_type=offering_type)
        start_mem = None

    db = get_database()
    auctions_service = AuctionsService()
    scoring_service = DomainScoringService()

    try:
        async with _upload_status_lock:
            # Update status
            await db.update_csv_upload_progress(
                job_id=job_id,
                status='parsing',
                current_stage='parsing'
            )

            # Clear staging for this batch
            await _clear_staging_for_batch(db, job_id)

            # Helper to map offer types
            def get_offer_type(source_data: dict, fname: str) -> str:
                if auction_site.lower() == 'namesilo':
                    type_field = (source_data.get('Type') or '').lower().strip()
                    if 'offer' in type_field or 'counter' in type_field:
                        return 'buy_now'
                    elif 'expired' in type_field or 'backorder' in type_field:
                        return 'backorder'
                    return 'auction'
                elif auction_site.lower() == 'godaddy':
                    auction_type = (source_data.get('auctionType') or '').lower().strip()
                    return 'buy_now' if auction_type == 'buynow' else 'auction'
                elif 'buy_now' in fname.lower():
                    return 'buy_now'
                return offering_type or 'auction'

            # Parse and stream to staging
            iterator = auctions_service.load_auctions_from_csv(csv_content, auction_site, filename, is_file=is_file)

            # Reduced batch size for better stability with 1M+ record files
            BATCH_SIZE = 2500
            CHUNK_MAX_RECORDS = 50000
            
            batch_records = []
            total_parsed = 0
            total_skipped = 0
            chunk_parsed = 0
            
            total_inserted = 0
            total_updated = 0
            total_deleted = 0
            
            is_namecheap = auction_site.lower() == 'namecheap'

            for auction_input in iterator:
                try:
                    auction = auction_input.to_auction()

                    # Namecheap filter: skip if > 2 weeks future, BUT keep Buy Now domains
                    # Buy Now domains use a dummy date in 2099
                    if is_namecheap and auction.expiration_date:
                        two_weeks = datetime.now(timezone.utc) + timedelta(days=14)
                        is_far_future = auction.expiration_date.year > 2050
                        
                        if not is_far_future and auction.expiration_date > two_weeks:
                            total_skipped += 1
                            continue

                    # Safely extract first_seen and handle empty strings
                    first_seen_val = auction.source_data.get('registeredDate') if auction.source_data else None

                    def _clean_ts(ts):
                        if not ts: return None
                        if isinstance(ts, str) and ts.strip() == '': return None
                        return ts

                    record = {
                        'domain': auction.domain,
                        'auction_site': auction.auction_site,
                        'expiration_date': _clean_ts(auction.expiration_date.isoformat() if auction.expiration_date else None),
                        'start_date': _clean_ts(auction.start_date.isoformat() if auction.start_date else None),
                        'current_bid': auction.current_bid,
                        'link': auction.link,
                        'offer_type': get_offer_type(auction.source_data or {}, filename),
                        'source_data': auction.source_data,
                        'first_seen': _clean_ts(first_seen_val),
                        'import_batch_id': job_id
                    }

                    batch_records.append(record)
                    total_parsed += 1
                    chunk_parsed += 1

                    if len(batch_records) >= BATCH_SIZE:
                        await _insert_to_staging(db, batch_records, job_id)
                        batch_records = []

                        # More frequent heartbeats for large files
                        if total_parsed % 5000 == 0:
                            await db.update_csv_upload_progress(
                                job_id=job_id,
                                status='processing',
                                current_stage='parsing',
                                processed_records=total_parsed
                            )
                            # Yield to event loop for a moment
                            await asyncio.sleep(0.01)

                    if chunk_parsed >= CHUNK_MAX_RECORDS:
                        # Process the chunk right away
                        if batch_records:
                            await _insert_to_staging(db, batch_records, job_id)
                            batch_records = []
                        
                        logger.info("Processing chunk", job_id=job_id, chunk_records=chunk_parsed, total_parsed=total_parsed)
                        
                        await db.update_csv_upload_progress(
                            job_id=job_id, status='processing', current_stage='importing', processed_records=total_parsed
                        )
                        
                        try:
                            import_result = await _perform_atomic_import(db, auction_site, job_id, offering_type, cleanup_stale=False)
                            if import_result.get('success'):
                                total_inserted += (import_result.get('inserted') or 0)
                                total_updated += (import_result.get('updated') or 0)
                                total_deleted += (import_result.get('deleted') or 0)
                                new_domains = import_result.get('new_domains') or 0
                                
                                if new_domains > 0:
                                    await db.update_csv_upload_progress(
                                        job_id=job_id, status='processing', current_stage='scoring', processed_records=total_parsed
                                    )
                                    await _score_new_domains_after_import(
                                        db, job_id, scoring_service, fast_mode=(auction_site.lower() == 'namecheap')
                                    )
                        except Exception as import_err:
                            logger.error(f"Chunk import failed, but continuing", error=str(import_err))
                        finally:
                            # ALLWAYS clear staging and reset counter for the next chunk, even if it failed!
                            await _clear_staging_for_batch(db, job_id)
                            chunk_parsed = 0

                except Exception as e:
                    total_skipped += 1
                    logger.debug("Failed to process record", error=str(e))
                    continue

            # End of loop, process remaining chunk
            if batch_records or chunk_parsed > 0:
                if batch_records:
                    await _insert_to_staging(db, batch_records, job_id)
                
                logger.info("Processing final chunk", job_id=job_id, chunk_records=chunk_parsed, total_parsed=total_parsed)
                await db.update_csv_upload_progress(
                    job_id=job_id, status='processing', current_stage='importing', processed_records=total_parsed
                )
                import_result = await _perform_atomic_import(db, auction_site, job_id, offering_type, cleanup_stale=True)
                if import_result.get('success'):
                    total_inserted += (import_result.get('inserted') or 0)
                    total_updated += (import_result.get('updated') or 0)
                    total_deleted += (import_result.get('deleted') or 0)
                    new_domains = import_result.get('new_domains') or 0
                    
                    if new_domains > 0:
                        await db.update_csv_upload_progress(
                            job_id=job_id, status='processing', current_stage='scoring', processed_records=total_parsed
                        )
                        await _score_new_domains_after_import(
                            db, job_id, scoring_service, fast_mode=(auction_site.lower() == 'namecheap')
                        )
                # clear staging 
                await _clear_staging_for_batch(db, job_id)

            logger.info("Parsing and import complete", job_id=job_id, parsed=total_parsed, skipped=total_skipped)

            # Complete
            await db.update_csv_upload_progress(
                job_id=job_id,
                status='completed',
                current_stage='completed',
                processed_records=total_parsed,
                skipped_count=total_skipped,
                inserted_count=total_inserted,
                completed=True
            )
            logger.info(f"[CSV UPLOAD COMPLETE] {job_id}",
                       parsed=total_parsed,
                       inserted=total_inserted,
                       updated=total_updated,
                       deleted=total_deleted)

    except Exception as e:
        logger.error(f"[CSV UPLOAD FAILED] {job_id}", error=str(e))
        await db.update_csv_upload_progress(
            job_id=job_id,
            status='failed',
            error_message=str(e)[:500]
        )
        raise



class StorageProcessingRequest(BaseModel):
    storage_path: str
    filename: str
    auction_site: str
    offering_type: Optional[str] = 'auction'
    bucket: Optional[str] = "auction-csvs"


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


async def process_json_upload_async( job_id: str, json_content: str, filename: str, auction_site: str, offering_type: Optional[str] = None, is_file: bool = False ):
    """
    Background task to process JSON upload with progress tracking.
    Uses the optimized single-table staging approach.
    """
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        start_mem = process.memory_info().rss / 1024 / 1024
        logger.info(f"[JSON UPLOAD START] {job_id}", filename=filename, auction_site=auction_site, start_memory_mb=start_mem)
    except ImportError:
        logger.info(f"[JSON UPLOAD START] {job_id}", filename=filename, auction_site=auction_site)
        start_mem = None

    db = get_database()
    auctions_service = AuctionsService()
    scoring_service = DomainScoringService()

    try:
        async with _upload_status_lock:
            # Update status
            await db.update_csv_upload_progress(
                job_id=job_id,
                status='parsing',
                current_stage='parsing'
            )

            # Clear staging
            await _clear_staging_for_batch(db, job_id)

            # Parse JSON
            auction_inputs = auctions_service.load_auctions_from_json(json_content, auction_site, filename, is_file=is_file)

            if not auction_inputs:
                raise ValueError(f"JSON file is empty or contains no valid auction records")

            # Convert to staging records
            BATCH_SIZE = 5000
            CHUNK_MAX_RECORDS = 50000
            
            batch_records = []
            total_parsed = 0
            total_skipped = 0
            chunk_parsed = 0
            
            total_inserted = 0
            total_updated = 0
            total_deleted = 0

            for auction_input in auction_inputs:
                try:
                    auction = auction_input.to_auction()

                    # Extract offer_type from source_data for GoDaddy
                    record_offer_type = offering_type or 'auction'
                    if auction.auction_site.lower() == 'godaddy' and auction.source_data:
                        auction_type = auction.source_data.get('auctionType', '').strip()
                        if auction_type.lower() == 'buynow':
                            record_offer_type = 'buy_now'
                        elif auction_type.lower() == 'bid':
                            record_offer_type = 'auction'
                    
                    # Safely extract first_seen and handle empty strings
                    first_seen_val = auction.source_data.get('registeredDate') if auction.source_data else None

                    def _clean_ts(ts):
                        if not ts: return None
                        if isinstance(ts, str) and ts.strip() == '': return None
                        return ts

                    record = {
                        'domain': auction.domain,
                        'auction_site': auction.auction_site,
                        'expiration_date': _clean_ts(auction.expiration_date.isoformat() if auction.expiration_date else None),
                        'start_date': _clean_ts(auction.start_date.isoformat() if auction.start_date else None),
                        'current_bid': auction.current_bid,
                        'link': auction.link,
                        'offer_type': record_offer_type,
                        'source_data': auction.source_data,
                        'first_seen': _clean_ts(first_seen_val),
                        'import_batch_id': job_id
                    }

                    batch_records.append(record)
                    total_parsed += 1
                    chunk_parsed += 1

                    if len(batch_records) >= BATCH_SIZE:
                        await _insert_to_staging(db, batch_records, job_id)
                        batch_records = []

                        # More frequent heartbeats for large files
                        if total_parsed % 5000 == 0:
                            await db.update_csv_upload_progress(
                                job_id=job_id,
                                status='processing',
                                current_stage='parsing',
                                processed_records=total_parsed
                            )
                            # Yield to event loop for a moment
                            await asyncio.sleep(0.01)

                    if chunk_parsed >= CHUNK_MAX_RECORDS:
                        # Process the chunk right away
                        if batch_records:
                            await _insert_to_staging(db, batch_records, job_id)
                            batch_records = []
                        
                        logger.info("Processing JSON chunk", job_id=job_id, chunk_records=chunk_parsed, total_parsed=total_parsed)
                        
                        await db.update_csv_upload_progress(
                            job_id=job_id, status='processing', current_stage='importing', processed_records=total_parsed
                        )
                        try:
                            import_result = await _perform_atomic_import(db, auction_site, job_id, offering_type, cleanup_stale=False)
                            if import_result.get('success'):
                                total_inserted += (import_result.get('inserted') or 0)
                                total_updated += (import_result.get('updated') or 0)
                                total_deleted += (import_result.get('deleted') or 0)
                                new_domains = import_result.get('new_domains') or 0
                                
                                if new_domains > 0:
                                    await db.update_csv_upload_progress(
                                        job_id=job_id, status='processing', current_stage='scoring', processed_records=total_parsed
                                    )
                                    await _score_new_domains_after_import(
                                        db, job_id, scoring_service, fast_mode=False
                                    )
                        except Exception as import_err:
                            logger.error("JSON Chunk import failed, but continuing", error=str(import_err))
                        finally:
                            # ALLWAYS clear staging and reset counter for the next chunk, even if it failed!
                            await _clear_staging_for_batch(db, job_id)
                            chunk_parsed = 0

                except Exception as e:
                    total_skipped += 1
                    logger.debug("Failed to process JSON record", error=str(e))
                    continue

            # End of loop, process remaining chunk
            if batch_records or chunk_parsed > 0:
                if batch_records:
                    await _insert_to_staging(db, batch_records, job_id)
                
                logger.info("Processing final JSON chunk", job_id=job_id, chunk_records=chunk_parsed, total_parsed=total_parsed)
                await db.update_csv_upload_progress(
                    job_id=job_id, status='processing', current_stage='importing', processed_records=total_parsed
                )
                import_result = await _perform_atomic_import(db, auction_site, job_id, offering_type, cleanup_stale=True)
                if import_result.get('success'):
                    total_inserted += (import_result.get('inserted') or 0)
                    total_updated += (import_result.get('updated') or 0)
                    total_deleted += (import_result.get('deleted') or 0)
                    new_domains = import_result.get('new_domains') or 0
                    
                    if new_domains > 0:
                        await db.update_csv_upload_progress(
                            job_id=job_id, status='processing', current_stage='scoring', processed_records=total_parsed
                        )
                        await _score_new_domains_after_import(
                            db, job_id, scoring_service, fast_mode=False
                        )
                # clear staging 
                await _clear_staging_for_batch(db, job_id)

            logger.info("JSON parsing and import complete", job_id=job_id, parsed=total_parsed, skipped=total_skipped)

            # Complete
            await db.update_csv_upload_progress(
                job_id=job_id,
                status='completed',
                current_stage='completed',
                processed_records=total_parsed,
                skipped_count=total_skipped,
                inserted_count=total_inserted,
                completed=True
            )
            logger.info(f"[JSON UPLOAD COMPLETE] {job_id}",
                       parsed=total_parsed,
                       inserted=total_inserted,
                       updated=total_updated,
                       deleted=total_deleted)

    except Exception as e:
        logger.error(f"[JSON UPLOAD FAILED] {job_id}", error=str(e))
        await db.update_csv_upload_progress(
            job_id=job_id,
            status='failed',
            error_message=str(e)[:500]
        )
        raise


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


@router.post("/auctions/unlock-pipeline")
async def unlock_pipeline():
    """
    Emergency endpoint to reset the global upload lock and fail any stuck jobs.
    Use this if the pipeline is permanently stuck in 'waiting_for_lock'.
    """
    global _upload_status_lock
    try:
        # 1. Create a new lock to bypass any stuck waiters
        _upload_status_lock = asyncio.Lock()
        
        # 2. Mark any active jobs as failed in the database
        db = get_database()
        active_jobs = await ( await db._get_client() ).table('csv_upload_progress').select('job_id').in_('status', ['queued', 'parsing', 'processing']).execute()
        
        count = 0
        if active_jobs.data:
            for job in active_jobs.data:
                await db.update_csv_upload_progress( job_id=job['job_id'], status='failed', error_message="Pipeline manually unlocked - job cancelled." )
                count += 1
                
        logger.info("Pipeline manually unlocked", reset_jobs=count)
        return { "success": True, "message": f"Pipeline unlocked. {count} stuck jobs marked as failed." }
        
    except Exception as e:
        logger.error("Failed to unlock pipeline", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auctions/retry-job/{job_id}")
async def retry_auction_job(job_id: str):
    """
    Retry an existing upload job by pulling the file from storage again.
    This works for both CSV and JSON if they were successfully uploaded to storage.
    """
    try:
        db = get_database()
        progress = await db.get_csv_upload_progress(job_id)
        
        if not progress:
            raise HTTPException(status_code=404, detail="Job not found")
            
        filename = progress.get('filename')
        auction_site = progress.get('auction_site')
        offering_type = progress.get('offering_type', 'auction')
        
        if not filename:
            raise HTTPException(status_code=400, detail="Job record missing filename")

        # Reset progress in DB
        await db.update_csv_upload_progress( job_id=job_id, status='queued', current_stage='retrying', progress_percentage=0, error_message=None )
        
        # Trigger processing from storage
        # We assume the bucket is 'auction-csvs' and path is the filename as per upload_csv_to_storage
        bucket = "auction-csvs"
        path = filename 
        
        asyncio.create_task( process_file_from_storage_async( job_id=job_id, bucket=bucket, path=path, filename=filename, auction_site=auction_site, offering_type=offering_type ) )
        
        logger.info("Triggered retry for job", job_id=job_id, filename=filename)
        return { "success": True, "message": "Retry started in background.", "job_id": job_id }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retry job", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


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
