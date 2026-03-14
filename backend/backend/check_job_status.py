
import asyncio
import os
import sys
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def check_status():
    await init_database()
    db = get_database()
    
    print("\n--- JOB STATUS CHECK ---\n")
    
    # 1. Check csv_upload_progress for recent jobs
    try:
        res = db.client.table('csv_upload_progress')\
            .select('*')\
            .order('created_at', desc=True)\
            .limit(10)\
            .execute()
            
        print(f"{'Job ID':<38} | {'Filename':<30} | {'Status':<12} | {'Progress':<20} | {'Updated At'}")
        print("-" * 130)
        
        for job in res.data:
            job_id = job.get('job_id')
            filename = job.get('filename', 'N/A')
            status = job.get('status', 'N/A')
            processed = job.get('processed_records', 0)
            total = job.get('total_records', 0)
            percentage = f"{round(processed/total*100, 1)}%" if total else "N/A"
            updated = job.get('updated_at')
            
            # Shorten filename
            if len(filename) > 28:
                filename = filename[:25] + "..."
                
            print(f"{job_id:<38} | {filename:<30} | {status:<12} | {processed:>7}/{total:<7} ({percentage}) | {updated}")
            if status == 'failed':
                 print(f"   ERROR: {job.get('error_message')}")

    except Exception as e:
        print(f"Error fetching jobs: {e}")

    # 2. Check total count in auctions table
    print("\n--- AUCTIONS TABLE COUNT ---\n")
    try:
        count_res = db.client.table('auctions').select('*', count='exact', head=True).execute()
        print(f"Total Active Auctions: {count_res.count}")
    except Exception as e:
        print(f"Error counting auctions: {e}")

    # 3. Check staging count
    try:
        staging_res = db.client.table('auctions_staging').select('*', count='exact', head=True).execute()
        print(f"Total Staging Records: {staging_res.count}")
    except Exception as e:
        print(f"Error counting staging: {e}")

if __name__ == "__main__":
    asyncio.run(check_status())
