import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def check_staging():
    await init_database()
    db = get_database()
    
    # From debug_jobs.py output:
    # 26ca2907-e4d6-4041-8616-f0dd6d16e1bb | godaddy_tomorrow.json | completed | 52567
    tomorrow_job_id = "26ca2907-e4d6-4041-8616-f0dd6d16e1bb"
    
    print(f"\n--- CHECKING STAGING FOR JOB {tomorrow_job_id} ---\n")
    
    try:
        # Check count in staging
        res = db.client.table('auctions_staging')\
            .select('*', count='exact')\
            .eq('job_id', tomorrow_job_id)\
            .limit(1)\
            .execute()
            
        print(f"Records in auctions_staging for this job: {res.count}")
        
        if res.count > 0:
            print("\nData IS in staging! Inspecting sample dates...")
            
            sample = db.client.table('auctions_staging')\
                .select('domain, expiration_date')\
                .eq('job_id', tomorrow_job_id)\
                .limit(5)\
                .execute()
                
            for item in sample.data:
                print(f"  {item['domain']}: {item['expiration_date']}")
            
            print("\nIf data is here but not in 'auctions', the merge step failed or didn't run?")
        else:
            print("\nData is NOT in staging. It might have been deleted after merge (or attempted merge).")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_staging())
