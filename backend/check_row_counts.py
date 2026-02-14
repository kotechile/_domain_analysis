import asyncio
import structlog
from src.services.database import get_database, init_database

logger = structlog.get_logger()

async def check_counts():
    await init_database()
    db = get_database()

    print("\n--- Checking Table Counts ---")
    
    # Auctions
    try:
        res = db.client.table('auctions').select('count', count='exact').execute()
        count = res.count
        print(f"Auctions Table Count: {count}")
    except Exception as e:
        print(f"Error checking auctions: {e}")

    # Staging
    try:
        res = db.client.table('auctions_staging').select('count', count='exact').execute()
        count = res.count
        print(f"Staging Table Count: {count}")
    except Exception as e:
        print(f"Error checking staging: {e}")

    # Check recent uploads
    try:
        res = db.client.table('csv_upload_progress').select('*').order('created_at', desc=True).limit(5).execute()
        print("\n--- Recent Upload Jobs ---")
        for job in res.data:
            print(f"Job: {job.get('filename')} | Status: {job.get('status')} | Stage: {job.get('current_stage')} | Processed: {job.get('processed_records')}/{job.get('total_records')}")
    except Exception as e:
        print(f"Error checking upload progress: {e}")

if __name__ == "__main__":
    asyncio.run(check_counts())
