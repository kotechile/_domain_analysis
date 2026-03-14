import asyncio
import os
import sys
from dotenv import load_dotenv

# Setup paths and env
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
load_dotenv(os.path.join(os.path.dirname(__file__), 'src/.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from services.database import get_database, init_database

async def check_namesilo():
    print("Initializing...")
    await init_database()
    db = get_database()
    
    # Query for NameSilo jobs
    try:
        query = db.client.table('csv_upload_progress')\
            .select('*')\
            .eq('auction_site', 'namesilo')\
            .order('created_at', desc=True)\
            .limit(5)
            
        response = query.execute()
        jobs = response.data
        
        print(f"\nFound {len(jobs)} recent NameSilo jobs:")
        print("-" * 100)
        print(f"{'ID':<38} | {'Status':<10} | {'Records':<8} | {'Error'}")
        print("-" * 100)
        
        for job in jobs:
            job_id = job.get('id')
            status = job.get('status')
            records = job.get('records_processed', 0)
            error = job.get('error_message', '') or ''
            print(f"{job_id:<38} | {status:<10} | {records:<8} | {error}")
            
    except Exception as e:
        print(f"Error checking jobs: {e}")

if __name__ == "__main__":
    asyncio.run(check_namesilo())
