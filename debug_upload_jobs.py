
import os
import asyncio
from supabase import create_client

async def check_jobs():
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            print("Error: Missing SUPABASE_URL or SUPABASE_KEY in environment")
            return

        print(f"Connecting to Supabase: {url}")
        client = create_client(url, key)
        
        print("Fetching recent upload jobs...")
        result = client.table('csv_upload_progress')\
            .select('*')\
            .order('created_at', desc=True)\
            .limit(10)\
            .execute()
            
        jobs = result.data
        if not jobs:
            print("No jobs found in csv_upload_progress table.")
            # Verify we can insert a test record to ensure it works
            return

        print(f"\nFound {len(jobs)} recent jobs:\n")
        print(f"{'Time':<20} | {'Filename':<40} | {'Status':<10} | {'Processed':<10} | {'Total':<10} | {'Error'}")
        print("-" * 140)
        
        for job in jobs:
            created_at = job.get('created_at', '')[:19]
            filename = job.get('filename', '')
            if len(filename) > 40: filename = "..." + filename[-37:]
            status = job.get('status', 'unknown')
            processed = job.get('processed_records', 0)
            total = job.get('total_records', 0)
            error = job.get('error_message', '')
            if error and len(error) > 40: error = error[:40] + "..."
            
            print(f"{created_at:<20} | {filename:<40} | {status:<10} | {processed:<10} | {total:<10} | {error}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_jobs())
