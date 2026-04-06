"""
Optimized Auctions API routes - Performance-Optimized Import System
Replaces the 5-table parallel approach with single-table atomic import
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Body, BackgroundTasks
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import structlog
import uuid
import asyncio
import io

from services.auctions_service import AuctionsService
from services.database import get_database
from services.domain_scoring_service import DomainScoringService
from models.domain_analysis import NamecheapDomain

logger = structlog.get_logger()
router = APIRouter()

# Global lock to prevent concurrent uploads
_upload_status_lock = asyncio.Lock()


class StorageProcessingRequest(BaseModel):
    """Request model for processing from storage"""
    storage_path: str
    filename: str
    auction_site: str
    offering_type: Optional[str] = 'auction'
    bucket: Optional[str] = "auction-csvs"


async def _insert_batch_to_staging(db, records: List[Dict], import_batch_id: uuid.UUID) -> int:
    """
    Insert batch of records into auctions_import staging table.
    Returns number of records inserted.
    """
    if not records:
        return 0

    # Add import_batch_id to each record
    for record in records:
        record['import_batch_id'] = str(import_batch_id)

    client = await db._get_client()

    try:
        # Use larger batch size for better performance
        result = await client.table('auctions_import').insert(records).execute()
        return len(result.data) if result.data else 0
    except Exception as e:
        logger.error("Failed to insert staging batch", error=str(e), batch_size=len(records))
        raise


async def _run_optimized_import(
    db,
    import_batch_id: uuid.UUID,
    auction_site: str,
    offering_type: Optional[str],
    total_records: int
) -> Dict[str, Any]:
    """
    Run the optimized atomic import function.
    Single RPC call handles: UPSERT + DELETE + CLEANUP
    """
    logger.info("Starting atomic import", import_batch_id=str(import_batch_id), site=auction_site)

    client = await db._get_client()

    try:
        result = await client.rpc('import_auctions_batch', {
            'p_import_batch_id': str(import_batch_id),
            'p_auction_site': auction_site,
            'p_offering_type': offering_type
        }).execute()

        if not result.data:
            raise Exception("Import function returned no data")

        import_result = result.data[0] if isinstance(result.data, list) else result.data

        if not import_result.get('success'):
            raise Exception(f"Import failed: {import_result.get('error', 'Unknown error')}")

        logger.info("Atomic import complete",
                   import_batch_id=str(import_batch_id),
                   inserted=import_result.get('inserted'),
                   updated=import_result.get('updated'),
                   deleted=import_result.get('deleted'),
                   new_domains=import_result.get('new_domains'))

        return import_result

    except Exception as e:
        logger.error("Atomic import failed", error=str(e))
        raise


async def _score_new_domains(
    db,
    import_batch_id: uuid.UUID,
    auction_site: str,
    scoring_service: DomainScoringService,
    fast_mode: bool = False
) -> int:
    """
    Score only new domains after import.
    Fast mode: Batch update without individual updates.
    """
    logger.info("Starting post-import scoring",
               import_batch_id=str(import_batch_id),
               site=auction_site,
               fast_mode=fast_mode)

    client = await db._get_client()
    total_scored = 0

    try:
        # Get new domains that need scoring
        result = await client.rpc('get_new_domains_for_scoring', {
            'p_import_batch_id': str(import_batch_id),
            'p_limit': 5000  # Process in batches
        }).execute()

        if not result.data:
            logger.info("No new domains to score")
            return 0

        new_domains = result.data
        logger.info(f"Found {len(new_domains)} new domains to score")

        if fast_mode:
            # Fast mode: Score in Python, batch update
            scored_records = []
            for domain_record in new_domains:
                try:
                    namecheap_domain = NamecheapDomain(
                        name=domain_record['domain'],
                        registered_date=None,
                        url=None
                    )
                    scored = scoring_service.score_domain(namecheap_domain)

                    scored_records.append({
                        'domain': domain_record['domain'],
                        'auction_site': domain_record['auction_site'],
                        'expiration_date': domain_record['expiration_date'],
                        'score': scored.total_meaning_score if scored.total_meaning_score else 0,
                        'processed': True
                    })

                    if len(scored_records) >= 500:
                        # Batch update
                        await _batch_update_scores(client, scored_records)
                        total_scored += len(scored_records)
                        scored_records = []
                        await asyncio.sleep(0.01)  # Yield control

                except Exception as e:
                    logger.warning("Failed to score domain",
                                 domain=domain_record.get('domain'),
                                 error=str(e))

            # Update remaining
            if scored_records:
                await _batch_update_scores(client, scored_records)
                total_scored += len(scored_records)

        else:
            # Standard mode: Score one by one
            for domain_record in new_domains:
                try:
                    namecheap_domain = NamecheapDomain(
                        name=domain_record['domain'],
                        registered_date=None,
                        url=None
                    )
                    scored = scoring_service.score_domain(namecheap_domain)

                    await client.table('auctions').update({
                        'score': scored.total_meaning_score,
                        'processed': True
                    }).eq('domain', domain_record['domain']) \
                      .eq('auction_site', domain_record['auction_site']) \
                      .eq('expiration_date', domain_record['expiration_date']) \
                      .execute()

                    total_scored += 1

                    if total_scored % 100 == 0:
                        await asyncio.sleep(0.01)

                except Exception as e:
                    logger.warning("Failed to score domain",
                                 domain=domain_record.get('domain'),
                                 error=str(e))

        logger.info("Post-import scoring complete",
                   total_scored=total_scored,
                   import_batch_id=str(import_batch_id))

        return total_scored

    except Exception as e:
        logger.error("Post-import scoring failed", error=str(e))
        raise


async def _batch_update_scores(client, records: List[Dict]):
    """Batch update scores for better performance"""
    if not records:
        return

    # Build update query - use CASE statement for efficient bulk update
    # Since Supabase doesn't support CASE directly, we do individual updates
    # but with larger batches
    for record in records:
        try:
            await client.table('auctions').update({
                'score': record['score'],
                'processed': record['processed']
            }).eq('domain', record['domain']) \
              .eq('auction_site', record['auction_site']) \
              .eq('expiration_date', record['expiration_date']) \
              .execute()
        except Exception as e:
            logger.warning("Failed to update score",
                         domain=record.get('domain'),
                         error=str(e))


async def process_upload_optimized(
    job_id: str,
    csv_content: str,
    filename: str,
    auction_site: str,
    offering_type: Optional[str] = None,
    is_file: bool = False
):
    """
    Optimized upload processing with single staging table and atomic import.

    Flow:
    1. Parse CSV/JSON to auction objects
    2. Stream to staging table (auctions_import)
    3. Call atomic import function (UPSERT + DELETE + CLEANUP)
    4. Score new domains only
    """
    db = get_database()
    auctions_service = AuctionsService()
    import_batch_id = uuid.uuid4()

    try:
        logger.info(f"[OPTIMIZED UPLOAD START] {job_id}",
                   filename=filename,
                   auction_site=auction_site,
                   import_batch_id=str(import_batch_id))

        async with _upload_status_lock:
            # Update status
            await db.update_csv_upload_progress(
                job_id=job_id,
                status='parsing',
                current_stage='parsing'
            )

            # Get iterator from parser
            iterator = auctions_service.load_auctions_from_csv(
                csv_content, auction_site, filename, is_file=is_file
            )

            # Streaming insert to staging
            batch = []
            batch_size = 1000
            total_processed = 0
            skipped_count = 0

            await db.update_csv_upload_progress(
                job_id=job_id,
                status='processing',
                current_stage='streaming_to_staging'
            )

            # Determine if Namecheap (for filtering)
            is_namecheap = auction_site.lower() == 'namecheap'
            two_weeks_from_now = datetime.now(timezone.utc) + timedelta(days=14)

            for auction_input in iterator:
                try:
                    auction = auction_input.to_auction()

                    # Filter: Skip Namecheap auctions > 2 weeks out
                    if is_namecheap and auction.expiration_date:
                        if auction.expiration_date > two_weeks_from_now:
                            skipped_count += 1
                            continue

                    # Determine offer_type
                    record_offer_type = offering_type
                    if auction_site.lower() == 'namesilo' and auction.source_data:
                        type_field = auction.source_data.get('Type', '').strip()
                        record_offer_type = _map_namesilo_type(type_field)
                    elif auction_site.lower() == 'godaddy' and auction.source_data:
                        auction_type = auction.source_data.get('auctionType', '').strip()
                        if auction_type.lower() == 'buynow':
                            record_offer_type = 'buy_now'
                        elif auction_type.lower() == 'bid':
                            record_offer_type = 'auction'
                    elif auction_site.lower() == 'namecheap':
                        if 'buy_now' in filename.lower():
                            record_offer_type = 'buy_now'
                        else:
                            record_offer_type = 'auction'

                    # Build record
                    record = {
                        'domain': auction.domain,
                        'auction_site': auction.auction_site,
                        'expiration_date': auction.expiration_date.isoformat() if auction.expiration_date else None,
                        'start_date': auction.start_date.isoformat() if auction.start_date else None,
                        'current_bid': auction.current_bid,
                        'link': auction.link,
                        'offer_type': record_offer_type or 'auction',
                        'source_data': auction.source_data,
                        'first_seen': auction.source_data.get('registeredDate') if auction.source_data else None
                    }

                    batch.append(record)

                    if len(batch) >= batch_size:
                        inserted = await _insert_batch_to_staging(db, batch, import_batch_id)
                        total_processed += inserted

                        # Update progress
                        if total_processed % 5000 == 0:
                            await db.update_csv_upload_progress(
                                job_id=job_id,
                                status='processing',
                                current_stage='streaming_to_staging',
                                processed_records=total_processed
                            )
                            logger.info("Staging progress",
                                       job_id=job_id,
                                       processed=total_processed)

                        batch = []

                except Exception as e:
                    logger.warning("Failed to process auction record", error=str(e))
                    continue

            # Insert remaining batch
            if batch:
                inserted = await _insert_batch_to_staging(db, batch, import_batch_id)
                total_processed += inserted

            if total_processed == 0:
                error_msg = f"File contains no valid records. Site: {auction_site}"
                await db.update_csv_upload_progress(
                    job_id=job_id,
                    status='failed',
                    error_message=error_msg
                )
                return

            logger.info("Staging complete",
                       job_id=job_id,
                       total_staged=total_processed,
                       skipped=skipped_count)

            # Run atomic import
            await db.update_csv_upload_progress(
                job_id=job_id,
                status='processing',
                current_stage='importing',
                processed_records=total_processed,
                skipped_count=skipped_count
            )

            import_result = await _run_optimized_import(
                db, import_batch_id, auction_site, offering_type, total_processed
            )

            # Score new domains
            await db.update_csv_upload_progress(
                job_id=job_id,
                status='processing',
                current_stage='scoring',
                processed_records=total_processed
            )

            scoring_service = DomainScoringService()
            scored_count = await _score_new_domains(
                db, import_batch_id, auction_site, scoring_service,
                fast_mode=(auction_site.lower() == 'namecheap')
            )

            # Complete
            await db.update_csv_upload_progress(
                job_id=job_id,
                status='completed',
                current_stage='completed',
                processed_records=total_processed,
                skipped_count=skipped_count,
                inserted_count=import_result.get('inserted', 0),
                completed=True
            )

            logger.info(f"[OPTIMIZED UPLOAD COMPLETE] {job_id}",
                       processed=total_processed,
                       skipped=skipped_count,
                       inserted=import_result.get('inserted'),
                       updated=import_result.get('updated'),
                       deleted=import_result.get('deleted'),
                       new_domains_scored=scored_count)

    except Exception as e:
        logger.error(f"[OPTIMIZED UPLOAD FAILED] {job_id}", error=str(e))
        await db.update_csv_upload_progress(
            job_id=job_id,
            status='failed',
            error_message=str(e)[:500]
        )


def _map_namesilo_type(type_field: str) -> str:
    """Map NameSilo Type field to offer_type"""
    if not type_field:
        return 'auction'

    type_lower = type_field.lower().strip()

    if 'offer/counter' in type_lower or 'offer' in type_lower:
        return 'buy_now'
    elif type_lower == 'auction':
        return 'auction'
    elif type_lower == 'expired':
        return 'backorder'
    elif 'customer auction' in type_lower:
        return 'auction'
    elif 'expired domain auction' in type_lower:
        return 'backorder'
    elif 'backorder' in type_lower:
        return 'backorder'
    else:
        return 'auction'


# Export the optimized process function
__all__ = ['process_upload_optimized', 'StorageProcessingRequest']
