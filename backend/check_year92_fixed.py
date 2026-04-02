import asyncio
import os
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from services.database import DatabaseService

async def check_domain():
    # Use a dummy settings object with the env vars
    from utils.config import get_settings
    settings = get_settings()
    settings.SUPABASE_VERIFY_SSL = False
    
    db = DatabaseService()
    await db._get_client() # Initialize client
    
    domain = 'year92.com'.lower()
    client = await db._get_client()
    # Handle SSL manually if needed (Supabase JS library/Python library needs it
    res = await client.table('auctions').select('*').ilike('domain', domain).execute()
    
    if res.data:
        for r in res.data:
            print(f"Domain: {r['domain']}, Site: {r.get('auction_site')}, Offer Type: {r.get('offer_type')}")
            print(f"Full Record Keys: {list(r.keys())}")
            print(f"Deletion Flag: {r.get('deletion_flag')}")
            print(f"To Delete: {r.get('to_delete')}")
    else:
        print(f"Domain {domain} not found in auctions table.")

if __name__ == "__main__":
    asyncio.run(check_domain())
