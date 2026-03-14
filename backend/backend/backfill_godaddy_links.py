import asyncio
import structlog
from services.database import init_database, get_database

# Configure logger
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

async def backfill_links():
    await init_database()
    db = get_database()
    
    logger.info("Starting GoDaddy links backfill...")
    
    # 1. Get total count of GoDaddy auctions
    count_response = db.client.table('auctions').select('count', count='exact').eq('auction_site', 'godaddy').execute()
    total = count_response.count
    logger.info("Found records to process", total=total)
    
    if total == 0:
        print("No GoDaddy auctions found.")
        return

    # 2. Process in batches
    batch_size = 500
    processed = 0
    updated = 0
    
    while processed < total:
        # Fetch batch
        response = db.client.table('auctions') \
            .select('domain, source_data, link') \
            .eq('auction_site', 'godaddy') \
            .range(processed, processed + batch_size - 1) \
            .execute()
            
        batch = response.data
        if not batch:
            break
            
        logger.info("Processing batch", start=processed, size=len(batch))
        
        for row in batch:
            domain = row.get('domain')
            current_link = row.get('link')
            source_data = row.get('source_data') or {}
            
            # Extract link from source_data
            new_link = source_data.get('link') or source_data.get('url')
            
            # Only update if we have a new link and it's different (or current is None)
            if new_link and new_link != current_link:
                try:
                    db.client.table('auctions').update({'link': new_link}).eq('domain', domain).execute()
                    updated += 1
                except Exception as e:
                    logger.error("Failed to update record", domain=domain, error=str(e))
        
        processed += len(batch)
        print(f"Processed {processed}/{total} records. Updated: {updated}")
        
    logger.info("Backfill completed", total=total, updated=updated)
    print(f"✅ Backfill completed! Updated {updated} records.")

if __name__ == "__main__":
    asyncio.run(backfill_links())
