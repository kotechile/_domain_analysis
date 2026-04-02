import asyncio
import os
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from services.database import get_database

async def check_domain():
    db = get_database()
    client = await db._get_client()
    
    domain = 'year92.com'.lower()
    res = await client.table('auctions').select('*').ilike('domain', domain).execute()
    
    if res.data:
        for r in res.data:
            print(f"Domain: {r['domain']}, Site: {r['auction_site']}, Offer Type: {r['offer_type']}, To Delete: {r['to_delete']}")
    else:
        print(f"Domain {domain} not found in auctions table.")

if __name__ == "__main__":
    asyncio.run(check_domain())
