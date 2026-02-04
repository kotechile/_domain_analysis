import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from services.database import DatabaseService

async def debug_schema():
    db = DatabaseService()
    # Try inserting a dummy record with job_id
    test_job_id = "00000000-0000-0000-0000-000000000000"
    try:
        res = db.client.table('auctions_staging').insert({
            'domain': 'test-isolation.com',
            'expiration_date': '2099-01-01',
            'auction_site': 'test',
            'job_id': test_job_id
        }).execute()
        print("✅ Successfully inserted test record with job_id")
        
        # Verify it has the job_id
        res_check = db.client.table('auctions_staging').select('job_id').eq('domain', 'test-isolation.com').execute()
        print("Verification result:", res_check.data)
        
        # Cleanup
        db.client.table('auctions_staging').delete().eq('domain', 'test-isolation.com').execute()
    except Exception as e:
        print(f"❌ Failed to insert/verify job_id: {e}")

if __name__ == "__main__":
    asyncio.run(debug_schema())
