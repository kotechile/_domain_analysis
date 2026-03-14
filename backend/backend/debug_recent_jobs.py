import asyncio
import os
import sys
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def check_recent_jobs():
    await init_database()
    db = get_database()
    
    print("\n--- RECENT UPLOAD JOBS ---\n")
    
    try:
        # Check specific job IDs from user logs
        target_jobs = [
            '3f2a1fad-aa16-48d4-84a9-79c9e0bd8738', # namesilo (newest)
            '26ca2907-e4d6-4041-8616-f0dd6d16e1bb', # godaddy (merging)
            '893307b9-9163-4dd6-a866-2202b35c53d5'  # namecheap (scoring complete)
        ]
        
        print(f"Checking for {len(target_jobs)} specific jobs...")
        
        res = db.client.table('csv_upload_progress').select('*').in_('job_id', target_jobs).execute()
        
        if not res.data:
            print("No matching jobs found.")
        
        for job in res.data:
            print(f"Job ID: {job.get('job_id')}")
            print(f"File: {job.get('filename')} ({job.get('auction_site')})")
            print(f"Status: {job.get('status')}")
            print(f"Stage: {job.get('current_stage')}")
            print(f"Progress: {job.get('processed_records')}/{job.get('total_records')}")
            print(f"Error: {job.get('error_message')}")
            print(f"Created: {job.get('created_at')}")
            print(f"Updated: {job.get('updated_at')}")
            print("-" * 30)
            
    except Exception as e:
        print(f"Error fetching jobs: {e}")

if __name__ == "__main__":
    asyncio.run(check_recent_jobs())
