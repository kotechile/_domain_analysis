import asyncio
import os
import sys
from collections import Counter

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def check_sites():
    await init_database()
    db = get_database()
    
    print("\n--- DISTINCT AUCTION SITES ---\n")
    
    try:
        # Check for NULL or empty auction_site
        print("Checking for NULL or empty auction_site...")
        # Note: filtering for NULL might need .is_('auction_site', 'null')
        res_null = db.client.table('auctions').select('id', count='exact').is_('auction_site', 'null').limit(1).execute()
        print(f"  NULL auction_site count: {res_null.count}")
        
        # Check for empty string
        res_empty = db.client.table('auctions').select('id', count='exact').eq('auction_site', '').limit(1).execute()
        print(f"  Empty string auction_site count: {res_empty.count}")

        # Check for common variants
        variants = ['namesilo', 'NameSilo', 'NAMESILO', 'namecheap', 'godaddy']
        for v in variants:
            res = db.client.table('auctions').select('id', count='exact').eq('auction_site', v).limit(1).execute()
            print(f"  '{v}': {res.count}")
            
        # Check total count to see if numbers add up
        res_total = db.client.table('auctions').select('id', count='exact').limit(1).execute()
        print(f"\n  Total records: {res_total.count}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_sites())
