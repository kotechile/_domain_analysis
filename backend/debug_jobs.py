import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def list_jobs():
    await init_database()
    db = get_database()
    
    print("\n--- RECENT IMPORT JOBS ---\n")
    
    try:
        # Fetch recent jobs
        res = db.client.table('csv_upload_progress')\
            .select('*')\
            .order('created_at', desc=True)\
            .limit(10)\
            .execute()
            
        if not res.data:
            print("No jobs found.")
            return

        print(f"{'Job ID':<38} | {'Site':<10} | {'Status':<10} | {'Records':<8} | {'Error'}")
        print("-" * 150)
        
        for job in res.data:
            job_id = job.get('job_id')
            site = job.get('auction_site', 'N/A')
            status = job.get('status')
            records = job.get('total_records', 0)
            error = job.get('error_message', '') or ''
            
            # Truncate error if too long
            if len(error) > 80:
                error = error[:77] + "..."
                
            print(f"{job_id:<38} | {site:<10} | {status:<10} | {records:<8} | {error}")

        # Check if we have any data from 'godaddy_tomorrow.json'
        print("\n--- CHECKING GODADDY TOMORROW DATA ---\n")
        tomorrow_job = next((j for j in res.data if 'tomorrow' in j.get('filename', '')), None)
        
        if tomorrow_job:
            job_id = tomorrow_job['job_id']
            print(f"Found 'tomorrow' job: {job_id}")
            
            # Count records in auctions table for this job
            count_res = db.client.table('auctions')\
                .select('*', count='exact')\
                .eq('job_id', job_id)\
                .limit(1)\
                .execute()
                
            print(f"Records in 'auctions' table for this job: {count_res.count}")
            
            if count_res.count > 0:
                # Check expiration dates for this job
                sample_res = db.client.table('auctions')\
                    .select('domain, expiration_date')\
                    .eq('job_id', job_id)\
                    .limit(5)\
                    .execute()
                    
                print("Sample Expiration Dates for 'Tomorrow' file:")
                for item in sample_res.data:
                    print(f"  {item['domain']}: {item['expiration_date']}")
        else:
            print("No recent job found with 'tomorrow' in filename.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(list_jobs())
