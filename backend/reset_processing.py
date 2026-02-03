import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.database import DatabaseService

async def reset_processing():
    db = DatabaseService()
    if not db.client:
        print("❌ Failed to initialize Supabase client.")
        return

    print("--- 1. Clearing Auctions Staging Table ---")
    try:
        # Delete all records from staging
        res = db.client.table('auctions_staging').delete().neq('domain', 'forcing-delete-all').execute()
        print(f"Cleared staging table.")
    except Exception as e:
        print(f"Error clearing staging: {e}")

    print("\n--- 2. Resetting Stuck Jobs in csv_upload_progress ---")
    try:
        # Find all non-completed, non-failed jobs
        res = db.client.table('csv_upload_progress').select('job_id, status').not_.in_('status', ['completed', 'failed']).execute()
        if res.data:
            print(f"Found {len(res.data)} stuck jobs. Marking as failed...")
            for job in res.data:
                db.client.table('csv_upload_progress').update({
                    'status': 'failed',
                    'error_message': 'Reset manually by admin to resolve interference.'
                }).eq('job_id', job['job_id']).execute()
                print(f"Marked Job {job['job_id']} as failed.")
        else:
            print("No stuck jobs found.")
    except Exception as e:
        print(f"Error resetting jobs: {e}")

    print("\n--- 3. Verifying Main Auctions Table Site Counts ---")
    try:
        sites = ['godaddy', 'namecheap', 'namesilo']
        for site in sites:
            res = db.client.table('auctions').select('domain', count='exact').eq('auction_site', site).execute()
            print(f"Site: {site}, Count: {res.count}")
    except Exception as e:
        print(f"Error checking auctions: {e}")

if __name__ == "__main__":
    asyncio.run(reset_processing())
