"""
Auctions API routes for multi-source domain auction data
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Body, BackgroundTasks
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timezone
import structlog
import uuid
import asyncio

from services.auctions_service import AuctionsService
from services.database import get_database
from services.n8n_service import N8NService
from services.auction_scoring_service import AuctionScoringService
from services.domain_scoring_service import DomainScoringService
from services.external_apis import WaybackMachineService, DataForSEOService
from models.auctions import AuctionReportItem
from models.domain_analysis import NamecheapDomain

logger = structlog.get_logger()
router = APIRouter()


async def _clear_staging_chunked(db, auction_site: str, job_id: str):
    """
    Clear staging table for a specific site in chunks to avoid statement timeouts.
    """
    logger.info("Clearing staging table in chunks", job_id=job_id, site=auction_site)
    total_cleared = 0
    while True:
        # Fetch domains for this job
        clear_res = db.client.table('auctions_staging').select('domain').eq('job_id', job_id).limit(5000).execute()
        if not clear_res.data:
            break
        
        domains_to_del = [r['domain'] for r in clear_res.data]
        # Use small sub-batches for IN filter to avoid URL length limit
        for j in range(0, len(domains_to_del), 100):
            sub_domains = domains_to_del[j:j + 100]
            db.client.table('auctions_staging').delete().eq('job_id', job_id).in_('domain', sub_domains).execute()
        
        total_cleared += len(domains_to_del)
        await asyncio.sleep(0.01)
    
    logger.info("Staging table cleared successfully", job_id=job_id, site=auction_site, total=total_cleared)
    return total_cleared


async def _perform_python_chunked_merge(db, auction_site: str, job_id: str):
    """
    Perform merging from staging to main table in chunks from Python
    to avoid database statement timeouts.
    """
    logger.info("Starting chunked merge from Python", job_id=job_id, site=auction_site)
    
    total_merged = 0
    
    while True:
        # 1. Fetch a batch of records from staging
        result = db.client.table('auctions_staging').select('*').eq('job_id', job_id).limit(5000).execute()
        records = result.data
        
        if not records:
            break
            
        # 2. Prepare for upsert to main table
        # 2. Prepare for upsert to main table
        # Deduplicate records based on domain and auction_site to prevent 
        # "ON CONFLICT DO UPDATE command cannot affect row a second time" error.
        unique_records = {} 
        for r in records:
            # We key by domain + auction_site to be safe. 
            # If the DB unique constraint is stricter (e.g. includes expiration), this still works.
            # If the DB unique constraint is looser (e.g. just domain+site), this prevents the error.
            key = (r.get('domain'), r.get('auction_site'))
            
            # Extract link from source_data if not present
            link = r.get('link')
            source_data = r.get('source_data') or {}
            if not link and isinstance(source_data, dict):
                link = source_data.get('link')
            
            clean_r = {
                'domain': r.get('domain'),
                'start_date': r.get('start_date'),
                'expiration_date': r.get('expiration_date'),
                'auction_site': r.get('auction_site'),
                'current_bid': r.get('current_bid'),
                'source_data': r.get('source_data'),
                'link': link,
                'processed': r.get('processed', True),
                'preferred': r.get('preferred', False),
                'has_statistics': r.get('has_statistics', False),
                'score': r.get('score'),
                'offer_type': r.get('offer_type')
            }
            # Overwrite existing - assuming later records in batch might be newer or identical
            unique_records[key] = clean_r
            
        main_records = list(unique_records.values())
        
        # 3. Upsert to main table
        try:
            db.client.table('auctions').upsert(
                main_records, 
                on_conflict='domain,auction_site,expiration_date'
            ).execute()
            
            # 4. Delete merged records from staging in small sub-batches
            # Use smaller batches for the IN filter to avoid "URL component 'query' too long" (max ~2000 chars)
            domains = [r['domain'] for r in records]
            sub_batch_size = 100 # Safe size for URLs
            for j in range(0, len(domains), sub_batch_size):
                sub_domains = domains[j:j + sub_batch_size]
                db.client.table('auctions_staging').delete().eq('job_id', job_id).in_('domain', sub_domains).execute()
            
            total_merged += len(records)
            logger.info("Merged batch successfully", job_id=job_id, site=auction_site, count=len(records), total=total_merged)
            
            # Update progress
            await db.update_csv_upload_progress(
                job_id=job_id,
                current_stage='merging',
                inserted_count=total_merged
            )
            
        except Exception as e:
            logger.error("Failed to merge batch in Python", job_id=job_id, site=auction_site, error=str(e))
            raise
            
        await asyncio.sleep(0.1)
    
    # Post-merge cleanup
    try:
        # db.client.table('auctions').delete().lt('expiration_date', current_time).execute()
        # Use optimized chunked deletion to prevent timeouts
        await db.delete_expired_auctions()
    except Exception as e:
        logger.warning("Failed to delete expired domains", error=str(e))

    return total_merged


async def process_csv_upload_async(
    job_id: str,
    csv_content: str,
    filename: str,
    auction_site: str,
    offering_type: Optional[str] = None,
    is_file: bool = False
):
    """
    Background task to process CSV upload with progress tracking using streaming
    
    Args:
        job_id: Unique job identifier
        csv_content: CSV file content as string OR file path if is_file=True
        filename: Original filename
        auction_site: Auction site source
        is_file: Whether csv_content is a file path
    """
    db = get_database()
    auctions_service = AuctionsService()
    
    try:
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
        await db.update_csv_upload_progress(
            job_id=job_id,
            status='parsing',
            current_stage='parsing',
            total_records=total_records if total_records > 0 else None
        )
        
        # 2. Clear Staging for this Job ID to ensure clean slate
        try:
            await _clear_staging_chunked(db, auction_site, job_id)
        except Exception as e:
            logger.warning("Failed to clear staging (might be empty), continuing", job_id=job_id, error=str(e))

        # 3. Stream & Process
        # Helper function to map NameSilo Type field to offer_type
        def map_namesilo_type_to_offer_type(type_field: str) -> str:
            if not type_field:
                return 'auction'
            type_lower = type_field.lower().strip()
            if 'customer auction' in type_lower:
                return 'auction'
            elif 'expired domain auction' in type_lower:
                return 'auction'
            elif 'offer' in type_lower or 'counter' in type_lower:
                # Offer/Counter Offer is treated as buy_now
                return 'buy_now'
            elif 'backorder' in type_lower:
                return 'backorder'
            else:
                return 'auction'

        logger.info("Starting streaming process", job_id=job_id, auction_site=auction_site)
        
        # Get generator
        iterator = auctions_service.load_auctions_from_csv(csv_content, auction_site, filename, is_file=is_file)
        
        scoring_service = DomainScoringService()
        
        BATCH_SIZE = 2000
        batch_list = []
        processed_count = 0
        scored_count = 0
        passed_count = 0
        failed_count = 0
        skipped_count = 0
        
        # For NameSilo type stats
        namesilo_type_counts = {}
        
        async def process_batch(batch, is_last=False):
            nonlocal processed_count, scored_count, passed_count, failed_count, skipped_count
            
            if not batch:
                return

            # Insert into staging
            # Prepare staging records (remove 'ranking', 'score' if None, etc.)
            staging_batch = []
            for record in batch:
                # Create a clean dict for staging
                staging_record = {k: v for k, v in record.items() if k not in ['ranking']}
                
                # Cleanup specific fields
                if 'offer_type' in staging_record and not staging_record['offer_type']:
                     del staging_record['offer_type']
                     
                staging_batch.append(staging_record)
            
            # Retry logic for insert
            max_retries = 2
            inserted = False
            for retry in range(max_retries + 1):
                try:
                    if retry > 0:
                        await asyncio.sleep(1.0 * retry)
                        
                    db.client.table('auctions_staging').insert(staging_batch).execute()
                    inserted = True
                    break
                except Exception as insert_err:
                    if retry == max_retries:
                         logger.error("Failed to insert batch to staging", job_id=job_id, error=str(insert_err))
                         # We don't raise here to allow partial success if possible? 
                         # Actually if staging insert fails, we probably should fail the job or at least log heavily
            
            if inserted:
                processed_count += len(batch)
                
                # Update progress
                # Yield control
                await asyncio.sleep(0.01)
                
                try:
                    await db.update_csv_upload_progress(
                        job_id=job_id,
                        status='processing',
                        processed_records=processed_count,
                        current_stage='processing_batch',
                        total_records=total_records if total_records > 0 else processed_count # Update total if we go over
                    )
                except Exception:
                    pass # Ignore progress update errors

        # Loop through iterator
        for auction_input in iterator:
            try:
                auction = auction_input.to_auction()
                
                # Logic copied from original process_csv_upload_async
                # ... score ...
                # ... map types ...
                
                # Convert date types for JSON serialization (Supabase expects ISO strings)
                start_date_iso = auction.start_date.isoformat() if auction.start_date else None
                expiration_date = auction.expiration_date
                
                # NameSilo fallback
                if not expiration_date and auction_site.lower() == 'namesilo':
                     expiration_date = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
                
                expiration_date_iso = expiration_date.isoformat() if expiration_date else None

                namecheap_domain = NamecheapDomain(
                    name=auction.domain,
                    registered_date=None, # Extract from source_data if needed
                    url=None,
                    start_date=auction.start_date,
                    end_date=auction.expiration_date,
                    price=None
                )
                
                # Score
                scored = scoring_service.score_domain(namecheap_domain)
                scored_count += 1
                
                if scored.filter_status == 'PASS':
                    passed_count += 1
                else:
                    failed_count += 1

                score_value = scored.total_meaning_score if scored.total_meaning_score is not None else None
                
                # Determine offer_type
                record_offer_type = offering_type
                if auction_site.lower() == 'namesilo':
                    type_field = auction.source_data.get('Type', '').strip() if auction.source_data else ''
                    record_offer_type = map_namesilo_type_to_offer_type(type_field)
                    namesilo_type_counts[type_field] = namesilo_type_counts.get(type_field, 0) + 1
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
                
                auction_dict = {
                    'domain': auction.domain,
                    'start_date': start_date_iso,
                    'expiration_date': expiration_date_iso,
                    'auction_site': auction.auction_site,
                    'current_bid': auction.current_bid,
                    'source_data': auction.source_data,
                    'link': auction.link,
                    'processed': True,
                    'preferred': False,
                    'has_statistics': False,
                    'score': score_value,
                    'ranking': None,
                    'first_seen': first_seen_date,
                    'deletion_flag': False, # Default
                    'offer_type': record_offer_type,
                    'job_id': job_id
                }
                
                batch_list.append(auction_dict)
                
                if len(batch_list) >= BATCH_SIZE:
                    await process_batch(batch_list)
                    batch_list = []
                    
            except Exception as e:
                logger.warning("Failed to process auction record", domain=auction_input.domain if auction_input else '?', error=str(e))
                skipped_count += 1
        
        # Process remaining
        if batch_list:
            await process_batch(batch_list, is_last=True)
            
        logger.info("Streaming complete", 
                   job_id=job_id, 
                   processed=processed_count, 
                   passed=passed_count, 
                   failed=failed_count,
                   skipped=skipped_count,
                   namesilo_counts=namesilo_type_counts)
                   
        if processed_count == 0 and skipped_count == 0:
             # Empty file case
             error_msg = f"CSV file is empty or contains no valid auction records. Auction site: {auction_site}"
             logger.error(error_msg, job_id=job_id)
             await db.update_csv_upload_progress(
                job_id=job_id,
                status='failed',
                error_message=error_msg
            )
             return

        # 4. Merge Staging to Main
        await db.update_csv_upload_progress(
            job_id=job_id,
            status='processing',
            current_stage='merging',
            processed_records=processed_count
        )
        
        logger.info("Merging staging to main table", job_id=job_id)
        
        # Call SQL function
        # process_staging_data takes p_job_id
        try:
             # Use the specialized DB function if available, or generic merge
             # Assuming process_staging_data(p_job_id, p_auction_site)
             # Check database.py for signature logic if needed, but direct RPC is best
             
             # Calling `process_staging_data` rpc
             merge_result = db.client.rpc('process_staging_data', {
                 'p_job_id': job_id,
                 'p_auction_site': auction_site
                 # p_integration_type? 
             }).execute()
             
             # Calculate stats from merge result if returned, otherwise use local counts
             # Usually process_staging_data returns {inserted: X, updated: Y, ...}
             merge_stats = merge_result.data if merge_result.data else {}
             logger.info("Merge complete", stats=merge_stats)
             
        except Exception as merge_err:
             logger.error("Merge failed", error=str(merge_err), job_id=job_id)
             # Try to surface error but don't fail complete job if possible? 
             # No, merge failure is critical.
             raise merge_err

        # 5. Success
        await db.update_csv_upload_progress(
            job_id=job_id,
            status='completed',
            current_stage='completed',
            processed_records=processed_count,
            skipped_count=skipped_count,
            completed=True
        )
        
    except Exception as e:
        logger.error("An unexpected error occurred during CSV processing", job_id=job_id, error=str(e), exc_info=True)
        await db.update_csv_upload_progress(
            job_id=job_id,
            status='failed',
            error_message=f"An unexpected error occurred: {str(e)}"
        )


async def process_json_upload_async(
    job_id: str,
    json_content: str,
    filename: str,
    auction_site: str,
    offering_type: Optional[str] = None,
    is_file: bool = False
):
    """
    Background task to process JSON upload with progress tracking
    """
    db = get_database()
    auctions_service = AuctionsService()
    
    try:
        # Update status to parsing
        await db.update_csv_upload_progress(
            job_id=job_id,
            status='parsing',
            current_stage='parsing'
        )
        
        # Parse JSON using auctions service
        logger.info("Parsing JSON content", job_id=job_id, auction_site=auction_site, filename=filename, is_file=is_file)
        auction_inputs = auctions_service.load_auctions_from_json(json_content, auction_site, filename, is_file=is_file)
        
        if not auction_inputs:
            error_msg = f"JSON file is empty or contains no valid auction records. Auction site: {auction_site}, Filename: {filename}"
            logger.error(error_msg, job_id=job_id, auction_site=auction_site, filename=filename)
            await db.update_csv_upload_progress(
                job_id=job_id,
                status='failed',
                error_message=error_msg
            )
            return
        
        total_records = len(auction_inputs)
        
        # Update status to processing
        await db.update_csv_upload_progress(
            job_id=job_id,
            status='processing',
            total_records=total_records,
            current_stage='scoring'
        )
        
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
                
                # Use the offering_type from parameter
                record_offer_type = offering_type or 'auction'
                
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
                            try:
                                date_str = reg_date.strip()
                                if date_str.endswith('Z'):
                                    date_str = date_str[:-1] + '+00:00'
                                registered_date = datetime.fromisoformat(date_str)
                            except:
                                registered_date = None
                        elif isinstance(reg_date, datetime):
                            registered_date = reg_date
                
                namecheap_domain = NamecheapDomain(
                    name=auction.domain,
                    registered_date=registered_date,
                    url=None,
                    start_date=auction.start_date,
                    end_date=auction.expiration_date,
                    price=None,
                    bid_count=None,
                    ahrefs_domain_rating=None,
                    umbrella_ranking=None,
                    cloudflare_ranking=None,
                    estibot_value=None,
                    extensions_taken=None,
                    keyword_search_count=None,
                    last_sold_price=None,
                    last_sold_year=None,
                    is_partner_sale=None,
                    semrush_a_score=None,
                    majestic_citation=None,
                    ahrefs_backlinks=None,
                    semrush_backlinks=None,
                    majestic_backlinks=None,
                    majestic_trust_flow=None,
                    go_value=None
                )
                
                # Score domain
                scored = scoring_service.score_domain(namecheap_domain)
                scored_count += 1
                
                score_value = scored.total_meaning_score if scored.total_meaning_score is not None else None
                
                auction_dict = {
                    'domain': auction.domain,
                    'start_date': auction.start_date.isoformat() if auction.start_date else None,
                    'expiration_date': auction.expiration_date.isoformat() if auction.expiration_date else None,
                    'auction_site': auction.auction_site,
                    'current_bid': auction.current_bid,
                    'source_data': auction.source_data,
                    'link': auction.link,
                    'processed': True,
                    'preferred': False,
                    'has_statistics': False,
                    'score': score_value,
                    'ranking': None,
                    'offer_type': record_offer_type,
                    'job_id': job_id
                }
                
                if scored.filter_status == 'PASS':
                    passed_count += 1
                else:
                    failed_count += 1
                
                auction_dicts.append(auction_dict)
            except Exception as e:
                skipped_count += 1
                continue
            
            # Keep event loop responsive for health checks
            if (idx + 1) % 500 == 0:
                await asyncio.sleep(0.01)
                
            if (idx + 1) % 1000 == 0:
                await db.update_csv_upload_progress(
                    job_id=job_id,
                    processed_records=idx + 1,
                    skipped_count=skipped_count,
                    current_stage='scoring'
                )

        # Update stage
        await db.update_csv_upload_progress(
            job_id=job_id,
            processed_records=len(auction_dicts),
            skipped_count=skipped_count,
            current_stage='loading_staging'
        )

        # Loading and Merging (simplified logic)
        if db.client:
             # General "Mark & Sweep" cleanup logic - Mark Phase - DISABLED
             effective_offering_type = offering_type or 'auction'
             logger.info("Marking records for deletion (cleanup phase 1) - DISABLED", 
                       job_id=job_id, 
                       auction_site=auction_site,
                       offering_type=effective_offering_type)
             
             # try:
             #     # Build the base query
             #     mark_query = db.client.table('auctions').update({'deletion_flag': True}).eq('auction_site', auction_site)
             #     
             #     # Apply scope rules
             #     if auction_site.lower() != 'namesilo':
             #         mark_query = mark_query.eq('offer_type', effective_offering_type)
             #     
             #     mark_result = mark_query.execute()
             #     marked_count = len(mark_result.data) if mark_result.data else 0
             #     
             #     logger.info("Marked records for deletion", 
             #               job_id=job_id,
             #               count=marked_count,
             #               scope_site=auction_site,
             #               scope_type=effective_offering_type if auction_site.lower() != 'namesilo' else 'ALL')
             # except Exception as e:
             #     logger.warning("Failed to mark records for deletion", job_id=job_id, error=str(e))

             # Clear
             # Use chunked delete helper
             await _clear_staging_chunked(db, auction_site, job_id)
             
             # Insert in batches
             batch_size = 5000
             for i in range(0, len(auction_dicts), batch_size):
                 batch = auction_dicts[i:i + batch_size]
                 staging_batch = [{k: v for k, v in r.items() if k != 'ranking'} for r in batch]
                 db.client.table('auctions_staging').insert(staging_batch).execute()
                 # Small sleep to yield control
                 await asyncio.sleep(0.01)
             
             # Merge using robust Python-based chunked merge
             merged_count = await _perform_python_chunked_merge(db, auction_site, job_id)
             inserted_count = merged_count

             # Cleanup (Sweep phase) - DISABLED
             deleted_count = 0
             # logger.info("Cleaning up stale records (cleanup phase 2)", job_id=job_id)
             # try:
             #     # Build the base query
             #     delete_query = db.client.table('auctions').delete().eq('auction_site', auction_site).eq('deletion_flag', True)
             #     
             #     # Apply same scope rules as Mark phase
             #     # Use effective_offering_type
             #     effective_offering_type = offering_type or 'auction'
             #     if auction_site.lower() != 'namesilo':
             #          delete_query = delete_query.eq('offer_type', effective_offering_type)
             #     
             #     delete_result = delete_query.execute()
             #     deleted_count = len(delete_result.data) if delete_result.data else 0
             #     
             #     logger.info("Cleanup complete: deleted stale records", 
             #               job_id=job_id, 
             #               deleted=deleted_count,
             #               site=auction_site)
             #               
             # except Exception as e:
             #     logger.error("Failed to cleanup stale records", job_id=job_id, error=str(e))

             result = {
                'inserted': inserted_count,
                'updated': 0,
                'skipped': 0,
                'total': total_records,
                'deleted': deleted_count
             }

        # Final update
        await db.update_csv_upload_progress(
            job_id=job_id,
            status='completed',
            current_stage='completed',
            processed_records=total_records,
            completed=True
        )
        
    except Exception as e:
        error_msg = f"Failed to process JSON upload: {str(e)}"
        await db.update_csv_upload_progress(
            job_id=job_id,
            status='failed',
            error_message=error_msg
        )





@router.post("/auctions/upload-csv")
async def upload_auctions_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auction_site: str = Query(..., description="Auction site name (e.g., namecheap, godaddy)"),
    offering_type: str = Query('auction', description="Offering type (auction, backorder, buy_now)"),
):
    """
    Upload auctions CSV file.
    
    
    This endpoint:
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
            
        # Create job entry (so we have a record even before processing starts)
        db = get_database()
        await db.create_csv_upload_job(
            job_id=job_id,
            filename=safe_filename,
            auction_site=auction_site,
            offering_type=offering_type
        )
        
        # Start background task that handles BOTH upload to storage AND processing
        background_tasks.add_task(
            background_handle_upload_and_process,
            job_id=job_id,
            local_path=temp_path,
            filename=safe_filename,
            auction_site=auction_site,
            offering_type=offering_type
        )
        
        logger.info("File accepted for async processing", 
                   filename=safe_filename, 
                   job_id=job_id,
                   temp_path=temp_path)
            
        return {
            "success": True,
            "message": "File accepted. Upload to storage and processing started in background.",
            "filename": safe_filename,
            "job_id": job_id,
            "n8n_triggered": False 
        }
        
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
async def process_existing_upload(
    request: StorageProcessingRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger processing for a file already uploaded to Supabase Storage.
    
    Use this to bypass backend upload limits/timeouts. 
    Upload directly to Supabase Storage from client (e.g. N8N), then call this.
    """
    try:
        job_id = str(uuid.uuid4())
        
        # Start background processing directly (job creation is handled in the background task)
        db = get_database()
        
        # Start background processing directly
        background_tasks.add_task(
            process_file_from_storage_async,
            job_id=job_id,
            bucket=request.bucket,
            path=request.storage_path,
            filename=request.filename,
            auction_site=request.auction_site,
            offering_type=request.offering_type
        )
        
        logger.info("Triggered processing for existing storage file", 
                   filename=request.filename, 
                   job_id=job_id,
                   storage_path=request.storage_path)
            
        return {
            "success": True,
            "message": "Processing started in background.",
            "job_id": job_id,
            "filename": request.filename
        }
        
    except Exception as e:
        logger.error("Failed to trigger storage processing", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to trigger processing: {str(e)}")


async def background_handle_upload_and_process(
    job_id: str,
    local_path: str,
    filename: str,
    auction_site: str,
    offering_type: str
):
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
        
        # 2. Process (using local path)
        is_json = filename.lower().endswith('.json')
        is_csv = filename.lower().endswith('.csv')
        
        if is_json:
            await process_json_upload_async(
                job_id=job_id,
                json_content=local_path,
                filename=filename,
                auction_site=auction_site,
                offering_type=offering_type,
                is_file=True
            )
        elif is_csv:
            await process_csv_upload_async(
                job_id=job_id,
                csv_content=local_path,
                filename=filename,
                auction_site=auction_site,
                offering_type=offering_type,
                is_file=True
            )
            
    except Exception as e:
        logger.error("Background upload/processing failed", job_id=job_id, error=str(e), exc_info=True)
        try:
            db = get_database()
            await db.update_csv_upload_progress(
                job_id=job_id,
                status='failed',
                error_message=str(e)
            )
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
async def upload_auctions_json(
    file: UploadFile = File(...),
    auction_site: str = Query(..., description="Auction site source: 'godaddy', etc."),
    offering_type: Optional[str] = Query(None, description="Type of domain offering: 'auction', 'backorder', 'buy_now'"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
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
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            content_chunks.append(chunk)
            total_size += len(chunk)
            logger.debug("Read chunk", chunk_size=len(chunk), total_size=total_size)
        
        # Combine chunks and decode to string
        content_bytes = b''.join(content_chunks)
        file_size_mb = round(total_size / (1024 * 1024), 2)
        
        logger.info("Received auctions JSON upload", 
                   job_id=job_id,
                   filename=file.filename, 
                   size=total_size,
                   size_mb=file_size_mb,
                   auction_site=detected_site)
        
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
        await db.create_csv_upload_job(
            job_id=job_id,
            filename=file.filename,
            auction_site=detected_site
        )
        
        # Start background processing
        background_tasks.add_task(
            process_json_upload_async,
            job_id=job_id,
            json_content=json_content,
            filename=file.filename,
            auction_site=detected_site,
            offering_type=detected_offering_type
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "message": "JSON upload started. Use /auctions/upload-progress/{job_id} to check progress.",
            "filename": file.filename,
            "auction_site": detected_site
        }
        
    except HTTPException:
        raise
    except MemoryError:
        logger.error("Out of memory while processing JSON", filename=file.filename)
        raise HTTPException(
            status_code=413, 
            detail="File is too large to process. Please split the file into smaller chunks or contact support."
        )
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        
        logger.error("Failed to upload auctions JSON", 
                    error=error_msg, 
                    error_type=error_type,
                    filename=file.filename,
                    exc_info=True)
        
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


async def process_file_from_storage_async(
    job_id: str,
    bucket: str,
    path: str,
    filename: str,
    auction_site: str,
    offering_type: Optional[str] = None
):
    """
    Background task to download and process file from storage using streaming and temp files
    """
    import tempfile
    import os
    
    temp_path = None
    
    try:
        db = get_database()
        
        # Create progress tracking job (moved from endpoint to prevent timeouts)
        await db.create_csv_upload_job(
            job_id=job_id,
            filename=filename,
            auction_site=auction_site,
            offering_type=offering_type
        )
        
        # Sanitize filename for temp file usage (replace slashes with underscores)
        # This prevents "No such file or directory" errors if filename contains folders
        safe_filename = filename.replace('/', '_').replace('\\', '_')
        
        # Create a unique temp file path
        # We do this INSIDE the try block to catch any FS errors
        temp_fd, temp_path = tempfile.mkstemp(suffix=f"_{safe_filename}")
        os.close(temp_fd) # Close file descriptor, we'll open it by path
        
        # Update status to downloading
        await db.update_csv_upload_progress(
            job_id=job_id,
            status='downloading',
            current_stage='downloading_from_storage'
        )
        
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
            await process_json_upload_async(
                job_id=job_id,
                json_content=temp_path,
                filename=filename,
                auction_site=auction_site,
                offering_type=offering_type,
                is_file=True
            )
        elif is_csv:
            # Process CSV using the file path
            await process_csv_upload_async(
                job_id=job_id,
                csv_content=temp_path,
                filename=filename,
                auction_site=auction_site,
                offering_type=offering_type,
                is_file=True
            )
        else:
            await db.update_csv_upload_progress(
                job_id=job_id,
                status='failed',
                error_message="File must be CSV or JSON"
            )
            logger.error("Invalid file type", job_id=job_id, filename=filename)
        
        # Check job status and delete file from storage if successful
        try:
            job_status = await db.get_csv_upload_progress(job_id)
            if job_status and job_status.get('status') == 'completed':
                logger.info("Job completed successfully, deleting file from storage", job_id=job_id, bucket=bucket, path=path)
                await db.delete_file_from_storage(bucket, path)
            else:
                logger.info("Job did not complete successfully, keeping file in storage", 
                           job_id=job_id, 
                           status=job_status.get('status') if job_status else 'unknown',
                           bucket=bucket, 
                           path=path)
        except Exception as cleanup_error:
            logger.warning("Failed to perform storage cleanup check", job_id=job_id, error=str(cleanup_error))
            
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to process file from storage", 
                    job_id=job_id,
                    bucket=bucket, 
                    path=path,
                    error=error_msg,
                    exc_info=True)
        
        try:
            db = get_database()
            # If job exists, update it. If create_job failed, this might also fail or update non-existent job.
            # But mostly create_job succeeds, and error happens later.
            await db.update_csv_upload_progress(
                job_id=job_id,
                status='failed',
                error_message=f"Storage processing failed: {error_msg}"
            )
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
async def process_from_storage(
    bucket: str = Body(..., description="Supabase storage bucket name"),
    path: str = Body(..., description="File path in storage"),
    auction_site: str = Body(..., description="Auction site source"),
    offering_type: Optional[str] = Body(None, description="Type of domain offering"),
    filename: Optional[str] = Body(None, description="Original filename"),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Process auction file from Supabase storage
    
    Returns immediately and processes the file in the background to avoid ngrok timeouts.
    Downloads the file from storage and processes it (CSV or JSON)
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
        
        # Create job in background to return immediately
        # db = get_database() call removed from here to avoid connection wait

        
        # Start background task to download and process file
        background_tasks.add_task(
            process_file_from_storage_async,
            job_id=job_id,
            bucket=bucket,
            path=path,
            filename=file_path,
            auction_site=auction_site,
            offering_type=offering_type
        )
        
        logger.info("File processing started in background", job_id=job_id, bucket=bucket, path=path)
        
        return {
            "success": True,
            "job_id": job_id,
            "message": f"{'JSON' if is_json else 'CSV'} processing started from storage. Use /auctions/upload-progress/{job_id} to check progress.",
            "filename": file_path,
            "auction_site": auction_site,
            "bucket": bucket,
            "path": path
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to initiate file processing from storage", 
                    bucket=bucket, 
                    path=path,
                    error=error_msg,
                    exc_info=True)
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
            raise HTTPException(
                status_code=404,
                detail="No active upload job found"
            )
        
        job_id = progress.get('job_id')
        return {
            "success": True,
            "job_id": job_id,
            "status": progress.get('status'),
            "filename": progress.get('filename'),
            "auction_site": progress.get('auction_site'),
            "total_records": progress.get('total_records', 0),
            "processed_records": progress.get('processed_records', 0),
            "inserted_count": progress.get('inserted_count', 0),
            "updated_count": progress.get('updated_count', 0),
            "skipped_count": progress.get('skipped_count', 0),
            "deleted_expired_count": progress.get('deleted_expired_count', 0),
            "current_stage": progress.get('current_stage'),
            "progress_percentage": progress.get('progress_percentage', 0.00),
            "error_message": progress.get('error_message'),
            "started_at": progress.get('started_at'),
            "updated_at": progress.get('updated_at'),
            "completed_at": progress.get('completed_at')
        }
        
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
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        return {
            "success": True,
            "job_id": job_id,
            "status": progress.get('status'),
            "filename": progress.get('filename'),
            "auction_site": progress.get('auction_site'),
            "total_records": progress.get('total_records', 0),
            "processed_records": progress.get('processed_records', 0),
            "inserted_count": progress.get('inserted_count', 0),
            "updated_count": progress.get('updated_count', 0),
            "skipped_count": progress.get('skipped_count', 0),
            "deleted_expired_count": progress.get('deleted_expired_count', 0),
            "current_stage": progress.get('current_stage'),
            "progress_percentage": progress.get('progress_percentage', 0.00),
            "error_message": progress.get('error_message'),
            "started_at": progress.get('started_at'),
            "updated_at": progress.get('updated_at'),
            "completed_at": progress.get('completed_at')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get upload progress", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")


@router.post("/auctions/upload-progress/{job_id}/mark-failed")
async def mark_job_as_failed(
    job_id: str,
    request: Optional[Dict[str, Any]] = Body(default=None, description="Optional request body with error_message")
):
    """
    Manually mark an upload job as failed
    
    Useful for stuck jobs that need to be marked as failed to stop frontend polling
    """
    try:
        db = get_database()
        progress = await db.get_csv_upload_progress(job_id)
        
        if not progress:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        if progress.get('status') in ['completed', 'failed']:
            raise HTTPException(
                status_code=400,
                detail=f"Job is already {progress.get('status')}"
            )
        
        # Get error message from request body or use default
        error_msg = (request.get('error_message') if request else None) or "Job marked as failed manually (appears to be stuck)"
        
        # Mark as failed
        await db.update_csv_upload_progress(
            job_id=job_id,
            status='failed',
            error_message=error_msg,
            current_stage='failed'
        )
        
        logger.info("Job marked as failed manually", job_id=job_id, error_message=error_msg)
        
        return {
            "success": True,
            "message": f"Job {job_id} marked as failed",
            "job_id": job_id,
            "error_message": error_msg
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to mark job as failed", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to mark job as failed: {str(e)}")


@router.post("/auctions/trigger-analysis")
async def trigger_auctions_analysis(
    limit: int = Query(100, description="Maximum number of unique domains to trigger (DataForSEO limit: 100 unique domains per request)", ge=1, le=100)
):
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
        
        # Get scored auctions without page_statistics (most recent first)
        auctions = await auctions_service.get_scored_auctions_without_page_statistics(limit=limit)
        
        if not auctions:
            return {
                "success": True,
                "message": "No scored domains without page_statistics found",
                "triggered_count": 0,
                "skipped_count": 0,
                "triggered_domains": []
            }
        
        domain_names = [a['domain'] for a in auctions]
        
        # Trigger DataForSEO analysis via N8N webhook
        n8n_service = N8NService()
        n8n_result = await n8n_service.trigger_bulk_page_summary_workflow(domain_names)
        
        if n8n_result:
            triggered_count = len(domain_names)
            logger.info("Triggered N8N workflow for bulk page summary", 
                       triggered=triggered_count,
                       request_id=n8n_result.get('request_id'))
            
            return {
                "success": True,
                "message": f"Triggered analysis for {triggered_count} domains",
                "triggered_count": triggered_count,
                "skipped_count": 0,
                "triggered_domains": domain_names[:100],  # Return first 100 for display
                "request_id": n8n_result.get('request_id')
            }
        else:
            logger.warning("Failed to trigger N8N workflow", domains=len(domain_names))
            return {
                "success": False,
                "message": "Failed to trigger N8N workflow",
                "triggered_count": 0,
                "skipped_count": len(domain_names),
                "triggered_domains": []
            }
        
    except Exception as e:
        logger.error("Failed to trigger auctions analysis", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger analysis: {str(e)}"
        )


@router.post("/auctions/trigger-bulk-rank")
async def trigger_bulk_rank_analysis(
    limit: int = Query(1000, description="Maximum number of domains to trigger (DataForSEO bulk rank limit: 1000 domains)", ge=1, le=1000)
):
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
        auctions = await auctions_service.get_scored_auctions_closest_to_expire(limit=limit)
        
        if not auctions:
            return {
                "success": True,
                "message": "No scored domains without rank found",
                "triggered_count": 0,
                "skipped_count": 0,
                "triggered_domains": []
            }
        
        domain_names = [a['domain'] for a in auctions]
        
        # Trigger DataForSEO bulk rank analysis via N8N webhook
        n8n_service = N8NService()
        n8n_result = await n8n_service.trigger_bulk_rank_workflow(domain_names)
        
        if n8n_result:
            triggered_count = len(domain_names)
            logger.info("Triggered N8N workflow for bulk rank", 
                       triggered=triggered_count,
                       request_id=n8n_result.get('request_id'))
            
            return {
                "success": True,
                "message": f"Triggered bulk rank analysis for {triggered_count} domains",
                "triggered_count": triggered_count,
                "skipped_count": 0,
                "triggered_domains": domain_names[:100],  # Return first 100 for display
                "request_id": n8n_result.get('request_id')
            }
        else:
            logger.warning("Failed to trigger N8N bulk rank workflow", domains=len(domain_names))
            return {
                "success": False,
                "message": "Failed to trigger N8N bulk rank workflow",
                "triggered_count": 0,
                "skipped_count": len(domain_names),
                "triggered_domains": []
            }
        
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to trigger auctions analysis", 
                    error=error_msg,
                    limit=limit)
        
        # Check if it's a timeout or connection error
        if 'timeout' in error_msg.lower() or 'connection' in error_msg.lower() or 'reset' in error_msg.lower():
            raise HTTPException(
                status_code=504, 
                detail=f"Database query timed out while fetching auctions. Error: {error_msg}"
            )
        
        raise HTTPException(status_code=500, detail=f"Failed to trigger analysis: {error_msg}")


@router.post("/auctions/trigger-bulk-traffic-data")
async def trigger_bulk_traffic_data_analysis(
    limit: int = Query(1000, description="Maximum number of domains to trigger (DataForSEO Labs API limit: 1000 domains per request)", ge=1, le=1000)
):
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
            return {
                "success": True,
                "message": "No scored domains without traffic_data found",
                "triggered_count": 0,
                "skipped_count": 0,
                "triggered_domains": []
            }
        
        domain_names = [a['domain'] for a in auctions]
        
        # Trigger DataForSEO Labs API traffic data collection via N8N webhook
        n8n_service = N8NService()
        n8n_result = await n8n_service.trigger_bulk_traffic_batch_workflow(domain_names)
        
        if n8n_result:
            triggered_count = len(domain_names)
            logger.info("Triggered N8N workflow for bulk traffic batch", 
                       triggered=triggered_count,
                       request_id=n8n_result.get('request_id'))
            
            return {
                "success": True,
                "message": f"Triggered traffic data collection for {triggered_count} domains",
                "triggered_count": triggered_count,
                "skipped_count": 0,
                "triggered_domains": domain_names[:100],  # Return first 100 for display
                "request_id": n8n_result.get('request_id')
            }
        else:
            logger.warning("Failed to trigger N8N traffic data workflow", domains=len(domain_names))
            return {
                "success": False,
                "message": "Failed to trigger N8N traffic data workflow",
                "triggered_count": 0,
                "skipped_count": len(domain_names),
                "triggered_domains": []
            }
        
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to trigger traffic data analysis", 
                    error=error_msg,
                    limit=limit)
        
        # Check if it's a timeout or connection error
        if 'timeout' in error_msg.lower() or 'connection' in error_msg.lower() or 'reset' in error_msg.lower():
            raise HTTPException(
                status_code=504, 
                detail=f"Database query timed out while fetching auctions. Error: {error_msg}"
            )
        
        raise HTTPException(status_code=500, detail=f"Failed to trigger traffic data analysis: {error_msg}")


@router.post("/auctions/trigger-bulk-spam-score")
async def trigger_bulk_spam_score_analysis(
    limit: int = Query(1000, description="Maximum number of domains to trigger (DataForSEO bulk spam score limit: 1000 domains)", ge=1, le=1000)
):
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
            return {
                "success": True,
                "message": "No scored domains without spam score found",
                "triggered_count": 0,
                "skipped_count": 0,
                "triggered_domains": []
            }
        
        domain_names = [a['domain'] for a in auctions]
        
        # Trigger DataForSEO bulk spam score analysis via N8N webhook
        n8n_service = N8NService()
        n8n_result = await n8n_service.trigger_bulk_spam_score_workflow(domain_names)
        
        if n8n_result:
            triggered_count = len(domain_names)
            logger.info("Triggered N8N workflow for bulk spam score", 
                       triggered=triggered_count,
                       request_id=n8n_result.get('request_id'))
            
            return {
                "success": True,
                "message": f"Triggered bulk spam score analysis for {triggered_count} domains",
                "triggered_count": triggered_count,
                "skipped_count": 0,
                "triggered_domains": domain_names[:100],  # Return first 100 for display
                "request_id": n8n_result.get('request_id')
            }
        else:
            logger.warning("Failed to trigger N8N bulk spam score workflow", domains=len(domain_names))
            return {
                "success": False,
                "message": "Failed to trigger N8N bulk spam score workflow",
                "triggered_count": 0,
                "skipped_count": len(domain_names),
                "triggered_domains": []
            }
        
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to trigger bulk spam score analysis", 
                    error=error_msg,
                    limit=limit)
        
        # Check if it's a timeout or connection error
        if 'timeout' in error_msg.lower() or 'connection' in error_msg.lower() or 'reset' in error_msg.lower():
            raise HTTPException(
                status_code=504, 
                detail=f"Database query timed out while fetching auctions. Error: {error_msg}"
            )
        
        raise HTTPException(status_code=500, detail=f"Failed to trigger bulk spam score analysis: {error_msg}")


@router.post("/auctions/trigger-bulk-backlinks")
async def trigger_bulk_backlinks_analysis(
    limit: int = Query(1000, description="Maximum number of domains to trigger (DataForSEO bulk backlinks limit: 1000 domains)", ge=1, le=1000)
):
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
            return {
                "success": True,
                "message": "No scored domains without backlinks found",
                "triggered_count": 0,
                "skipped_count": 0,
                "triggered_domains": []
            }
        
        domain_names = [a['domain'] for a in auctions]
        
        # Trigger DataForSEO bulk backlinks analysis via N8N webhook
        n8n_service = N8NService()
        n8n_result = await n8n_service.trigger_bulk_backlinks_workflow(domain_names)
        
        if n8n_result:
            triggered_count = len(domain_names)
            logger.info("Triggered N8N workflow for bulk backlinks", 
                       triggered=triggered_count,
                       request_id=n8n_result.get('request_id'))
            
            return {
                "success": True,
                "message": f"Triggered bulk backlinks analysis for {triggered_count} domains",
                "triggered_count": triggered_count,
                "skipped_count": 0,
                "triggered_domains": domain_names[:100],  # Return first 100 for display
                "request_id": n8n_result.get('request_id')
            }
        else:
            logger.warning("Failed to trigger N8N bulk backlinks workflow", domains=len(domain_names))
            return {
                "success": False,
                "message": "Failed to trigger N8N bulk backlinks workflow",
                "triggered_count": 0,
                "skipped_count": len(domain_names),
                "triggered_domains": []
            }
        
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to trigger bulk backlinks analysis", 
                    error=error_msg,
                    limit=limit)
        
        # Check if it's a timeout or connection error
        if 'timeout' in error_msg.lower() or 'connection' in error_msg.lower() or 'reset' in error_msg.lower():
            raise HTTPException(
                status_code=504, 
                detail=f"Database query timed out while fetching auctions. Error: {error_msg}"
            )
        
        raise HTTPException(status_code=500, detail=f"Failed to trigger bulk backlinks analysis: {error_msg}")

        raise HTTPException(status_code=500, detail=f"Failed to trigger bulk backlinks analysis: {error_msg}")


async def process_traffic_metrics_background_task(domains: list[str]):
    """
    Background task to fetch and save traffic metrics using DataForSEO Live API.
    """
    try:
        from services.external_apis import DataForSEOService
        from services.database import get_database
        
        service = DataForSEOService()
        db = get_database()
        
        logger.info("Starting background processing for traffic data", domains=len(domains))
        
        # Call Live API (this blocks this task but not the main thread)
        items = await service.fetch_bulk_traffic_estimation_live(domains)
        
        if items:
            logger.info("Traffic data retrieved", count=len(items))
            
            success_count = 0
            for item in items:
                # "item" structure based on verification:
                # { "se_type": "google", "target": "google.com", "metrics": { "organic": { "etv": ..., "count": ... } } }
                target = item.get('target')
                metrics = item.get('metrics', {})
                
                if target and metrics:
                    traffic_data = {
                        "organic_traffic": metrics.get('organic', {}).get('etv', 0),
                        "etv": metrics.get('organic', {}).get('etv', 0),
                        "organic_keywords": metrics.get('organic', {}).get('count', 0),
                        "traffic_timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Update DB
                    await db.update_auction_traffic_data(target, traffic_data)
                    success_count += 1
            
            logger.info("Traffic data processing completed", success_count=success_count)
        else:
            logger.warning("No traffic data items returned")
        
    except Exception as e:
        logger.error("Background traffic processing failed", error=str(e))


@router.post("/auctions/trigger-bulk-all-metrics")
async def trigger_bulk_all_metrics_analysis(
    preferred: Optional[bool] = Query(None, description="Filter by preferred status"),
    auction_site: Optional[str] = Query(None, description="Filter by auction site"),
    offering_type: Optional[str] = Query(None, description="Filter by market type: 'auction', 'backorder', 'buy_now'"),
    tld: Optional[str] = Query(None, description="Filter by TLD extension (e.g., '.com', '.ai') - deprecated, use tlds"),
    tlds: Optional[str] = Query(None, description="Comma-separated list of TLDs (e.g., '.com,.io,.ai')"),
    has_statistics: Optional[bool] = Query(None, description="Filter by has_statistics"),
    scored: Optional[bool] = Query(None, description="Filter by scored status (has score)"),
    min_rank: Optional[int] = Query(None, description="Minimum ranking", ge=1),
    max_rank: Optional[int] = Query(None, description="Maximum ranking", ge=1),
    min_score: Optional[float] = Query(None, description="Minimum score", ge=0, le=100),
    max_score: Optional[float] = Query(None, description="Maximum score", ge=0, le=100),
    expiration_from_date: Optional[str] = Query(None, description="Filter by expiration date from (YYYY-MM-DD)"),
    expiration_to_date: Optional[str] = Query(None, description="Filter by expiration date to (YYYY-MM-DD)"),
    sort_by: str = Query("expiration_date", description="Field to sort by"),
    sort_order: str = Query("asc", description="Sort order (asc, desc)"),
    limit: int = Query(1000, description="Maximum number of domains to trigger (1000 per analysis type)", ge=1, le=1000),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
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
        
        # Build filters (same as get_auctions_report)
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
        
        # Get auctions matching filters and missing any metric
        auctions = await auctions_service.get_auctions_missing_any_metric_with_filters(
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit
        )
        
        if not auctions:
            return {
                "success": True,
                "message": "No domains matching filters and missing any DataForSEO metric found",
                "triggered_count": 0,
                "skipped_count": 0,
                "triggered_domains": [],
                "results": {
                    "traffic_data": {"triggered": 0, "success": False},
                    "rank": {"triggered": 0, "success": False},
                    "backlinks": {"triggered": 0, "success": False},
                    "spam_score": {"triggered": 0, "success": False}
                }
            }
        
        domain_names = [a['domain'] for a in auctions]
        
        # Trigger all four analyses sequentially
        n8n_service = N8NService()
        results = {
            "traffic_data": {"triggered": 0, "success": False, "request_id": None, "error": None},
            "rank": {"triggered": 0, "success": False, "request_id": None, "error": None},
            "backlinks": {"triggered": 0, "success": False, "request_id": None, "error": None},
            "spam_score": {"triggered": 0, "success": False, "request_id": None, "error": None}
        }
        
        # 1. Traffic data
        try:
            logger.info("Triggering traffic data analysis (Direct API)", domains=len(domain_names))
            
            # Use Direct DataForSEO API (Background Processing)
            # Add background task to fetch and process data
            background_tasks.add_task(process_traffic_metrics_background_task, domain_names)
            
            results["traffic_data"] = {
                "triggered": len(domain_names),
                "success": True,
                "message": "Background processing started"
            }
            
            logger.info("Triggered traffic data background task", triggered=len(domain_names))
            
        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to trigger traffic data analysis", error=error_msg)
            results["traffic_data"]["error"] = error_msg
        
        # 2. Rank analysis
        try:
            logger.info("Triggering rank analysis", domains=len(domain_names))
            n8n_result = await n8n_service.trigger_bulk_rank_workflow(domain_names)
            if n8n_result:
                results["rank"] = {
                    "triggered": len(domain_names),
                    "success": True,
                    "request_id": n8n_result.get('request_id')
                }
                logger.info("Triggered rank analysis", 
                           triggered=len(domain_names),
                           request_id=n8n_result.get('request_id'))
            else:
                results["rank"]["error"] = "Failed to trigger N8N workflow"
        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to trigger rank analysis", error=error_msg)
            results["rank"]["error"] = error_msg
        
        # 3. Backlinks analysis
        try:
            logger.info("Triggering backlinks analysis", domains=len(domain_names))
            n8n_result = await n8n_service.trigger_bulk_backlinks_workflow(domain_names)
            if n8n_result:
                results["backlinks"] = {
                    "triggered": len(domain_names),
                    "success": True,
                    "request_id": n8n_result.get('request_id')
                }
                logger.info("Triggered backlinks analysis", 
                           triggered=len(domain_names),
                           request_id=n8n_result.get('request_id'))
            else:
                results["backlinks"]["error"] = "Failed to trigger N8N workflow"
        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to trigger backlinks analysis", error=error_msg)
            results["backlinks"]["error"] = error_msg
        
        # 4. Spam score analysis
        try:
            logger.info("Triggering spam score analysis", domains=len(domain_names))
            n8n_result = await n8n_service.trigger_bulk_spam_score_workflow(domain_names)
            if n8n_result:
                results["spam_score"] = {
                    "triggered": len(domain_names),
                    "success": True,
                    "request_id": n8n_result.get('request_id')
                }
                logger.info("Triggered spam score analysis", 
                           triggered=len(domain_names),
                           request_id=n8n_result.get('request_id'))
            else:
                results["spam_score"]["error"] = "Failed to trigger N8N workflow"
        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to trigger spam score analysis", error=error_msg)
            results["spam_score"]["error"] = error_msg
        
        # Calculate summary
        total_triggered = sum(r["triggered"] for r in results.values())
        success_count = sum(1 for r in results.values() if r["success"])
        failed_count = 4 - success_count
        
        return {
            "success": success_count > 0,  # Success if at least one workflow succeeded
            "message": f"Triggered analyses for {len(domain_names)} domains. {success_count} succeeded, {failed_count} failed.",
            "triggered_count": len(domain_names),
            "skipped_count": 0,
            "triggered_domains": domain_names[:100],  # Return first 100 for display
            "results": results
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to trigger bulk all metrics analysis", 
                    error=error_msg,
                    limit=limit)
        
        # Check if it's a timeout or connection error
        if 'timeout' in error_msg.lower() or 'connection' in error_msg.lower() or 'reset' in error_msg.lower():
            raise HTTPException(
                status_code=504, 
                detail=f"Database query timed out while fetching auctions. Error: {error_msg}"
            )
        
        raise HTTPException(status_code=500, detail=f"Failed to trigger bulk all metrics analysis: {error_msg}")


@router.get("/auctions/report")
async def get_auctions_report(
    preferred: Optional[bool] = Query(None, description="Filter by preferred status"),
    auction_site: Optional[str] = Query(None, description="Filter by auction site"),
    offering_type: Optional[str] = Query(None, description="Filter by market type: 'auction', 'backorder', 'buy_now'"),
    tld: Optional[str] = Query(None, description="Filter by TLD extension (e.g., '.com', '.ai') - deprecated, use tlds"),
    tlds: Optional[str] = Query(None, description="Comma-separated list of TLDs (e.g., '.com,.io,.ai')"),
    has_statistics: Optional[bool] = Query(None, description="Filter by has_statistics"),
    scored: Optional[bool] = Query(None, description="Filter by scored status (has score)"),
    min_rank: Optional[int] = Query(None, description="Minimum ranking", ge=1),
    max_rank: Optional[int] = Query(None, description="Maximum ranking", ge=1),
    min_score: Optional[float] = Query(None, description="Minimum score", ge=0, le=100),
    max_score: Optional[float] = Query(None, description="Maximum score", ge=0, le=100),
    expiration_from_date: Optional[str] = Query(None, description="Filter by expiration date from (YYYY-MM-DD)"),
    expiration_to_date: Optional[str] = Query(None, description="Filter by expiration date to (YYYY-MM-DD)"),
    auction_sites: Optional[str] = Query(None, description="Comma-separated list of auction sites (e.g., 'godaddy,namecheap')"),
    sort_by: str = Query("expiration_date", description="Field to sort by"),
    order: str = Query("asc", description="Sort order (asc, desc)"),
    limit: int = Query(50, description="Maximum number of records (reduced default to prevent timeouts)", ge=1, le=100),
    offset: int = Query(0, description="Number of records to skip", ge=0)
):
    """
    Get auctions report with page_statistics from auctions table
    
    Returns auctions with page_statistics when available.
    Records without statistics will have NULL page_statistics field.
    """
    try:
        # Build filters
        filters = {}
        if preferred is not None:
            filters['preferred'] = preferred
        if auction_sites:
            filters['auction_sites'] = [s.strip().lower() for s in auction_sites.split(',') if s.strip()]
        if auction_site:
            filters['auction_site'] = auction_site
        if offering_type:
            # Normalize offering_type to lowercase for consistency
            filters['offering_type'] = offering_type.lower().strip()
            logger.info("Setting offering_type filter", 
                        offering_type=filters['offering_type'],
                        original_value=offering_type)
            logger.debug("Setting offering_type filter", 
                        offering_type=offering_type,
                        filter_dict=filters)
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
            filters['expiration_from_date'] = expiration_from_date
        if expiration_to_date:
            filters['expiration_to_date'] = expiration_to_date
        
        auctions_service = AuctionsService()
        result = await auctions_service.get_auctions_report(
            filters=filters,
            sort_by=sort_by,
            order=order,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "count": result.get("count", 0),
            "total_count": result.get("total_count", 0),
            "has_more": result.get("has_more", False),
            "auctions": result.get("auctions", [])
        }
        
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        logger.error("Failed to get auctions report", 
                    error=error_msg,
                    error_type=error_type,
                    sort_by=sort_by,
                    order=order,
                    limit=limit,
                    offset=offset,
                    exc_info=True)
        
        # Check if it's a timeout or connection error
        if 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower():
            raise HTTPException(
                status_code=504, 
                detail=f"Database query timed out. {error_msg}"
            )
        elif 'connection' in error_msg.lower() or 'reset' in error_msg.lower() or 'no available server' in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail=f"Database connection error. {error_msg}"
            )
        elif 'not found' in error_msg.lower() or 'does not exist' in error_msg.lower() or '42703' in error_msg:
            # Only return 404 for actual missing resources, not for RPC function errors
            if 'rpc' in error_msg.lower() or 'function' in error_msg.lower() or '42703' in error_msg:
                # Log full error for debugging
                logger.error("Database function error", 
                           error=error_msg,
                           error_type=type(e).__name__,
                           exc_info=True)
                # Extract full error details
                full_error = error_msg
                if hasattr(e, 'args') and e.args:
                    if isinstance(e.args[0], dict):
                        full_error = str(e.args[0])
                    elif isinstance(e.args[0], str):
                        full_error = e.args[0]
                raise HTTPException(
                    status_code=500,
                    detail=f"Database function error (code 42703 = undefined column). The filter_auctions_by_tlds function may have a missing column. Please ensure migration 20250131000013_fix_tld_filter_function.sql is applied. Full error: {full_error}"
                )
            raise HTTPException(
                status_code=404,
                detail=f"Database table or resource not found. {error_msg}"
            )
        
        raise HTTPException(status_code=500, detail=f"Failed to retrieve auctions report: {error_msg}")


@router.post("/auctions/process-scoring-batch")
async def process_scoring_batch(
    batch_size: int = Query(10000, ge=1, le=50000, description="Number of records to process"),
    config_id: Optional[str] = Query(None, description="Optional scoring config ID"),
    recalculate_rankings: bool = Query(True, description="Recalculate global rankings after processing")
):
    """
    Process a batch of unprocessed auctions through the scoring pipeline.
    
    This endpoint:
    1. Fetches unprocessed records with pre-scoring from Supabase
    2. Calculates complex scores (LFS, semantic) in Python
    3. Updates scores back to database
    4. Optionally recalculates global rankings
    
    Returns processing statistics.
    """
    try:
        scoring_service = AuctionScoringService()
        result = await scoring_service.process_batch(
            batch_size=batch_size,
            config_id=config_id,
            recalculate_rankings_after=recalculate_rankings
        )
        return result
    except Exception as e:
        logger.error("Failed to process scoring batch", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auctions/scoring-stats")
async def get_scoring_stats():
    """
    Get statistics about auction scoring progress.
    
    Returns counts of processed, unprocessed, and scored records.
    """
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
    Recalculate global rankings and preferred flags for all scored auctions.
    
    This should be called periodically or after processing large batches.
    """
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
            wayback_data = await asyncio.wait_for(
                wayback_service.get_domain_history(domain),
                timeout=15.0  # 15 second timeout
            )
        except asyncio.TimeoutError:
            logger.warning("Wayback Machine request timed out", domain=domain)
            return {
                "success": False,
                "message": "Request timed out. Wayback Machine may be slow or unavailable.",
                "first_seen": None
            }
        except Exception as e:
            logger.error("Wayback Machine request failed", domain=domain, error=str(e))
            return {
                "success": False,
                "message": f"Failed to fetch from Wayback Machine: {str(e)}",
                "first_seen": None
            }
        
        if not wayback_data:
            logger.info("No Wayback Machine data returned", domain=domain)
            return {
                "success": False,
                "message": "No Wayback Machine data found for this domain",
                "first_seen": None
            }
        
        # Get the first capture timestamp
        captures = wayback_data.get('captures', [])
        if not captures:
            logger.info("No captures found in Wayback Machine data", domain=domain)
            return {
                "success": False,
                "message": "No captures found for this domain",
                "first_seen": None
            }
        
        # Find the earliest capture
        try:
            first_capture = min(captures, key=lambda x: x.get("timestamp", "99999999999999"))
            first_timestamp = first_capture.get("timestamp")
        except Exception as e:
            logger.error("Failed to find earliest capture", domain=domain, error=str(e))
            return {
                "success": False,
                "message": "Failed to process capture data",
                "first_seen": None
            }
        
        if not first_timestamp:
            return {
                "success": False,
                "message": "Invalid timestamp in capture data",
                "first_seen": None
            }
        
        # Parse timestamp (format: YYYYMMDDHHMMSS)
        try:
            first_seen_dt = datetime.strptime(first_timestamp, "%Y%m%d%H%M%S")
        except ValueError:
            # Try with just date part
            try:
                first_seen_dt = datetime.strptime(first_timestamp[:8], "%Y%m%d")
            except ValueError:
                logger.error("Failed to parse timestamp", domain=domain, timestamp=first_timestamp)
                return {
                    "success": False,
                    "message": "Failed to parse timestamp",
                    "first_seen": None
                }
        
        # Update all auction records for this domain with the first_seen date
        if not db.client:
            raise HTTPException(status_code=503, detail="Database connection not available")
        
        try:
            result = db.client.table('auctions').update({
                'first_seen': first_seen_dt.isoformat()
            }).eq('domain', domain).execute()
            
            updated_count = len(result.data) if result.data else 0
            
            logger.info("Updated first_seen from Wayback Machine", 
                       domain=domain, 
                       first_seen=first_seen_dt.isoformat(),
                       updated_count=updated_count)
            
            return {
                "success": True,
                "first_seen": first_seen_dt.isoformat(),
                "first_seen_year": first_seen_dt.year,
                "updated_count": updated_count
            }
        except Exception as e:
            logger.error("Failed to update database", domain=domain, error=str(e))
            return {
                "success": False,
                "message": f"Failed to update database: {str(e)}",
                "first_seen": None
            }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to fetch Wayback Machine first seen", 
                    domain=domain, error=error_msg, exc_info=True)
        return {
            "success": False,
            "message": f"Unexpected error: {error_msg}",
            "first_seen": None
        }


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
        queue_result = db.client.table('dataforseo_queue').select(
            'id,domain,expiration_date'
        ).eq('status', 'pending').order('expiration_date', desc=False).limit(100).execute()
        
        if not queue_result.data or len(queue_result.data) < 100:
            logger.info("Queue does not have 100 domains yet", count=len(queue_result.data) if queue_result.data else 0)
            return
        
        domains = [item['domain'] for item in queue_result.data]
        queue_ids = [item['id'] for item in queue_result.data]
        
        # Update queue items to 'processing'
        db.client.table('dataforseo_queue').update({
            'status': 'processing',
            'updated_at': datetime.now(timezone.utc).isoformat()
        }).in_('id', queue_ids).execute()
        
        logger.info("Processing DataForSEO queue", domain_count=len(domains))
        
        # Trigger DataForSEO analysis via N8N
        n8n_service = N8NService()
        n8n_result = await n8n_service.trigger_bulk_page_summary_workflow(domains)
        
        if n8n_result:
            logger.info("Triggered N8N workflow for queued domains", 
                       domain_count=len(domains),
                       request_id=n8n_result.get('request_id'))
            # Note: Queue items will be marked as 'completed' by the n8n webhook callback
            # when page_statistics are updated in the auctions table
        else:
            # Mark as failed if N8N trigger failed
            db.client.table('dataforseo_queue').update({
                'status': 'failed',
                'error_message': 'Failed to trigger N8N workflow',
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).in_('id', queue_ids).execute()
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
        auction_result = db.client.table('auctions').select(
            'id,domain,score,expiration_date,page_statistics'
        ).eq('domain', domain).limit(1).execute()
        
        if not auction_result.data or len(auction_result.data) == 0:
            return {
                "success": False,
                "message": "Domain not found in auctions table",
                "queued": False
            }
        
        auction = auction_result.data[0]
        
        # Check if domain is scored (score > 0)
        if not auction.get('score') or auction['score'] <= 0:
            return {
                "success": False,
                "message": "Domain must be scored (score > 0) to queue for DataForSEO analysis",
                "queued": False
            }
        
        # Check if domain already has page_statistics
        if auction.get('page_statistics'):
            return {
                "success": False,
                "message": "Domain already has DataForSEO data",
                "queued": False
            }
        
        # Check if domain is already in queue
        queue_check = db.client.table('dataforseo_queue').select('id,status').eq('domain', domain).limit(1).execute()
        if queue_check.data and len(queue_check.data) > 0:
            queue_item = queue_check.data[0]
            if queue_item['status'] == 'pending':
                # Get position in queue
                position_result = db.client.table('dataforseo_queue').select('id').eq('status', 'pending').order('expiration_date', desc=False).execute()
                position = None
                if position_result.data:
                    for idx, item in enumerate(position_result.data, 1):
                        if item['id'] == queue_item['id']:
                            position = idx
                            break
                
                queue_count = await get_queue_count()
                return {
                    "success": True,
                    "message": "Domain already in queue",
                    "queued": True,
                    "position": position,
                    "queue_count": queue_count
                }
        
        # Add to queue
        queue_data = {
            'domain': domain,
            'status': 'pending',
            'expiration_date': auction.get('expiration_date'),
            'score': auction.get('score'),
            'auction_id': auction.get('id')
        }
        
        result = db.client.table('dataforseo_queue').insert(queue_data).execute()
        
        # Get queue count
        queue_count = await get_queue_count()
        
        # Check if we've reached 100 and trigger processing
        if queue_count >= 100:
            # Trigger processing in background
            asyncio.create_task(process_dataforseo_queue())
        
        # Get position in queue (ordered by expiration_date ASC)
        position_result = db.client.table('dataforseo_queue').select('id').eq('status', 'pending').order('expiration_date', desc=False).execute()
        position = None
        if position_result.data:
            for idx, item in enumerate(position_result.data, 1):
                if item['id'] == result.data[0]['id']:
                    position = idx
                    break
        
        logger.info("Domain added to DataForSEO queue", domain=domain, position=position, queue_count=queue_count)
        
        return {
            "success": True,
            "message": "Domain added to queue",
            "queued": True,
            "position": position,
            "queue_count": queue_count,
            "will_process": queue_count >= 100
        }
        
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
        queue_count = await get_queue_count()
        
        result = {
            "queue_count": queue_count,
            "max_queue_size": 100,
            "ready_to_process": queue_count >= 100
        }
        
        # If domain provided, check position
        if domain:
            queue_item = db.client.table('dataforseo_queue').select('id,status').eq('domain', domain).eq('status', 'pending').limit(1).execute()
            if queue_item.data and len(queue_item.data) > 0:
                # Calculate position
                position_result = db.client.table('dataforseo_queue').select('id').eq('status', 'pending').order('expiration_date', desc=False).execute()
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
    cannot be cancelled.
    
    Returns success status
    """
    try:
        db = get_database()
        if not db.client:
            raise HTTPException(status_code=503, detail="Database connection not available")
        
        # Check if domain is in queue
        queue_check = db.client.table('dataforseo_queue').select('id,status').eq('domain', domain).limit(1).execute()
        
        if not queue_check.data or len(queue_check.data) == 0:
            return {
                "success": False,
                "message": "Domain not found in queue",
                "cancelled": False
            }
        
        queue_item = queue_check.data[0]
        
        # Only allow cancelling pending items
        if queue_item['status'] != 'pending':
            return {
                "success": False,
                "message": f"Cannot cancel domain with status '{queue_item['status']}'. Only pending requests can be cancelled.",
                "cancelled": False
            }
        
        # Delete from queue
        result = db.client.table('dataforseo_queue').delete().eq('id', queue_item['id']).execute()
        
        logger.info("Domain removed from DataForSEO queue", domain=domain)
        
        return {
            "success": True,
            "message": "Domain removed from queue",
            "cancelled": True
        }
        
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
    This endpoint can be called to clean up expired records at any time.
    
    Returns:
        Number of records deleted
    """
    try:
        db = get_database()
        deleted_count = await db.delete_expired_auctions()
        
        return {
            "success": True,
            "message": f"Deleted {deleted_count} expired auction(s)",
            "deleted_count": deleted_count
        }
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to delete expired auctions", error=error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete expired auctions: {error_msg}")

