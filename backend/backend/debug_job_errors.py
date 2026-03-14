import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def check_errors():
    await init_database()
    db = get_database()
    
    print("\n--- FAILED JOB ERRORS ---\n")
    
    try:
        # Fetch failed jobs
        res = db.client.table('csv_upload_progress')\
            .select('job_id, filename, status, error_message, created_at')\
            .eq('status', 'failed')\
            .order('created_at', desc=True)\
            .limit(10)\
            .execute()
            
        if not res.data:
            print("No failed jobs found in recent history.")
            return

        for job in res.data:
            print(f"Job ID: {job.get('job_id')}")
            print(f"Filename: {job.get('filename')}")
            print(f"Created: {job.get('created_at')}")
            print(f"Error: {job.get('error_message')}")
            print("-" * 50)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_errors())
