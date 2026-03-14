import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.database import get_database, init_database

async def check_recent_jobs():
    await init_database()
    db = get_database()
    
    if not db.client:
        print("Supabase client not available")
        return

    print("\n=== Recent CSV Upload Jobs ===\n")
    
    # Query latest 5 jobs from csv_upload_progress
    try:
        result = db.client.table('csv_upload_progress').select('*').order('created_at', desc=True).limit(5).execute()
        
        if result.data:
            for job in result.data:
                print(f"Job ID: {job['job_id']}")
                print(f"  Filename: {job.get('filename')}")
                print(f"  Status: {job.get('status')}")
                print(f"  Stage: {job.get('current_stage')}")
                print(f"  Processed: {job.get('processed_records')}/{job.get('total_records')}")
                print(f"  Created At: {job.get('created_at')}")
                if job.get('error_message'):
                    print(f"  Error: {job.get('error_message')}")
                print("-" * 30)
        else:
            print("No jobs found in csv_upload_progress table.")
            
        # Also check total auctions count
        auction_count = db.client.table('auctions').select('*', count='exact').limit(0).execute()
        print(f"\nTotal auctions in database: {auction_count.count}")
        
    except Exception as e:
        print(f"Error querying database: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_recent_jobs())
