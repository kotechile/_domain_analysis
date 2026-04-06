import asyncio
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from services.database import init_database

async def check():
    load_dotenv()
    db = await init_database()
    client = await db._get_client()
    
    # Force disable SSL verification for this test
    if hasattr(client, 'postgrest') and hasattr(client.postgrest, '_client'):
        client.postgrest._client.verify = False
    if hasattr(client, 'storage') and hasattr(client.storage, '_client'):
        client.storage._client.verify = False
    
    # Check auctions columns
    res = await client.table('auctions').select('*').limit(1).execute()
    if res.data:
        print(f"Auctions columns: {list(res.data[0].keys())}")
    else:
        print("Auctions table is empty, trying to query schema directly")
        # Try a quick RPC or query if available, or just insert/rollback
        pass

    # Check staging columns
    res_s = await client.table('auctions_staging_0').select('*').limit(1).execute()
    if res_s.data:
        print(f"Staging_0 columns: {list(res_s.data[0].keys())}")
    else:
        print("Staging_0 table is empty")

if __name__ == "__main__":
    asyncio.run(check())
