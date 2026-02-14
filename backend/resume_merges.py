import asyncio
import os
import sys
import structlog

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database
from api.routes.auctions import _perform_python_chunked_merge

logger = structlog.get_logger()

async def resume_merges():
    await init_database()
    db = get_database()
    
    print("\n--- RESUMING STUCK MERGES ---\n")
    
    # 1. Get unique job_ids from staging
    try:
        # Supabase client doesn't support 'distinct' easily on select directly with python client sometimes,
        # but we can fetch all job_ids (it's only 60k rows, maybe heavy but manageable if we just select job_id)
        # Better: use a remote procedure or just fetch unique via python set if list is small.
        # Actually 60k is small for job_ids list.
        
        print("Fetching unique job_ids from staging...")
        # We'll fetch in chunks just to be safe, but actually let's try a direct query if possible.
        # .select('job_id') returns all rows.
        
        # Let's use a smarter way: grouping is not native in postgrest select unless using RPC.
        # We will fetch all job_ids and dedupe in python. 
        # Since we have 61k records, fetching 61k UUID strings is roughly 2MB. Trivial.
        
        all_jobs_res = db.client.table('auctions_staging').select('job_id, auction_site').execute()
        
        if not all_jobs_res.data:
            print("No records found in staging.")
            return

        # Deduplicate to find unique (job_id, auction_site) pairs
        jobs_to_process = {}
        for row in all_jobs_res.data:
            jid = row.get('job_id')
            site = row.get('auction_site')
            if jid and site:
                jobs_to_process[jid] = site
        
        print(f"Found {len(jobs_to_process)} unique jobs to resume.")
        
        for job_id, site in jobs_to_process.items():
            print(f"Resuming merge for Job ID: {job_id} (Site: {site})...")
            try:
                count = await _perform_python_chunked_merge(db, site, job_id)
                print(f"  -> Successfully merged {count} records.")
            except Exception as e:
                print(f"  -> Failed to merge: {e}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(resume_merges())
