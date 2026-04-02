
import asyncio
import os
import sys

# Ensure backend directory is in path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database
from utils.config import get_settings

async def check_domain():
    # Initialize DB
    await init_database()
    db = get_database()
    client = await db._get_client()
    
    domain = 'year92.com'
    
    # Check auctions table
    res = await client.table('auctions').select('*').eq('domain', domain).execute()
    print(f"\n--- Checking domain: {domain} in auctions table ---")
    if res.data:
        for r in res.data:
            print(f"Auction Site: {r.get('auction_site')}")
            print(f"Offer Type: {r.get('offer_type')}")
            print(f"Expiration: {r.get('expiration_date')}")
            print(f"To Delete: {r.get('to_delete')}")
            print(f"ID: {r.get('id')}")
            print("-" * 20)
    else:
        print("Not found in auctions table.")

    # Check staging table
    res_staging = await client.table('auctions_staging').select('*').eq('domain', domain).execute()
    print(f"\n--- Checking domain: {domain} in auctions_staging table ---")
    if res_staging.data:
        for r in res_staging.data:
            print(f"Auction Site: {r.get('auction_site')}")
            print(f"Job ID: {r.get('job_id')}")
            print("-" * 20)
    else:
        print("Not found in auctions_staging table.")

if __name__ == "__main__":
    asyncio.run(check_domain())
