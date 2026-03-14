import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def debug_records():
    await init_database()
    db = get_database()
    
    print("\n--- DEBUGGING SPECIFIC RECORDS ---\n")
    
    try:
        # 1. Inspect a known GoDaddy record
        domain = 'lehiro.com'
        print(f"Checking details for {domain} (GoDaddy):")
        res = db.client.table('auctions').select('*').eq('domain', domain).execute()
        if res.data:
            item = res.data[0]
            print(f"  Auction Site: {item.get('auction_site')}")
            print(f"  Expiration: {item.get('expiration_date')}")
            print(f"  Offer Type: {item.get('offer_type')}")
            print(f"  Link: {item.get('link')}")
            print(f"  Source Data: {list(item.get('source_data', {}).keys())}")
        else:
            print("  Record not found!")

        # 2. Inspect 'gibe.xyz' (from 404 errors)
        domain = 'gibe.xyz'
        print(f"\nChecking details for {domain} (From 404s):")
        res = db.client.table('auctions').select('*').eq('domain', domain).execute()
        if res.data:
            item = res.data[0]
            print(f"  Auction Site: {item.get('auction_site')}")
            print(f"  Expiration: {item.get('expiration_date')}")
            print(f"  Offer Type: {item.get('offer_type')}")
        else:
            print("  Record not found!")

        # 3. Search for 'Buy Now' items with recent dates
        # This explains why User sees them with 2026 filter
        print("\nSearching for NameSilo/Namecheap items with dates < 2030:")
        query = db.client.table('auctions').select('domain, auction_site, expiration_date, offer_type')
        query = query.in_('auction_site', ['namesilo', 'namecheap'])
        query = query.lt('expiration_date', '2030-01-01')
        query = query.limit(10)
        
        res = query.execute()
        if res.data:
            print(f"  Found {len(res.data)} anomalies:")
            for item in res.data:
                 print(f"  {item['domain']} ({item['auction_site']}) - Exp: {item['expiration_date']}")
        else:
            print("  None found. All NameSilo/Namecheap items appear to be > 2030.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_records())
