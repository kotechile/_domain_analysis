import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from services.database import DatabaseService

async def check_db_counts():
    db = DatabaseService()
    if not db.client:
        print("❌ Failed to initialize Supabase client.")
        return

    print("--- Auctions Staging Counts ---")
    try:
        # Check Total counts
        res_total = db.client.table('auctions_staging').select('domain', count='exact').execute()
        print(f"Total records in staging: {res_total.count}")

        # Check records WITH job_id
        res_job = db.client.table('auctions_staging').select('job_id', count='exact').not_.is_('job_id', 'null').execute()
        print(f"Records with JOB_ID: {res_job.count}")

        # Check records WITHOUT job_id
        res_no_job = db.client.table('auctions_staging').select('job_id', count='exact').is_('job_id', 'null').execute()
        print(f"Records without JOB_ID (None): {res_no_job.count}")

        # Sample some job_ids
        if res_job.count > 0:
            res_samples = db.client.table('auctions_staging').select('job_id, auction_site').not_.is_('job_id', 'null').limit(10).execute()
            print("Sample active Jobs in staging:", res_samples.data)

    except Exception as e:
        print(f"Error checking staging: {e}")

    print("\n--- Auctions Main Table Counts ---")
    try:
        # Check counts per site
        sites = ['godaddy', 'namecheap', 'namesilo']
        for site in sites:
            res = db.client.table('auctions').select('domain', count='exact').eq('auction_site', site).execute()
            print(f"Site: {site}, Count: {res.count}")
    except Exception as e:
        print(f"Error checking auctions: {e}")

    print("\n--- Job Progress Status ---")
    try:
        res = db.client.table('csv_upload_progress').select('*').order('created_at', desc=True).limit(10).execute()
        for r in res.data:
            print(f"Job: {r['job_id']}, Site: {r['auction_site']}, Status: {r['status']}, Stage: {r['current_stage']}, Records: {r.get('processed_records', 0)}/{r.get('total_records', 0)}, Created: {r['created_at']}")
    except Exception as e:
        print(f"Error checking jobs: {e}")

if __name__ == "__main__":
    asyncio.run(check_db_counts())
