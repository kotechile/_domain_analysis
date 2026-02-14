import asyncio
import os
import sys
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def debug_filters():
    await init_database()
    db = get_database()
    
    print("\n--- DEBUGGING FILTER LOGIC (FASTER) ---\n")
    
    # Simulate the User's Filter: Feb 8 (yesterday) to Feb 10
    exp_from = "2026-02-08"
    exp_to = "2026-02-10T23:59:59"
    
    print(f"Querying Range: {exp_from} to {exp_to}")
    
    try:
        # 1. Fetch Sample Records (No Count)
        query = db.client.table('auctions').select('*')
        query = query.gte('expiration_date', exp_from)
        query = query.lte('expiration_date', exp_to)
        query = query.order('expiration_date', desc=False)
        query = query.limit(20)
        
        result = query.execute()
        
        if not result.data:
            print("\n  -> NO RECORDS FOUND within this date range.")
            
            # Debug: Check one GoDaddy record to see its exact date
            print("\nChecking a random GoDaddy record:")
            gd = db.client.table('auctions').select('domain, expiration_date').eq('auction_site', 'godaddy').limit(1).execute()
            print(f"  {gd.data}")
            
        else:
            print(f"\nFound {len(result.data)} records (limit 20). Sample:")
            for item in result.data:
                print(f"  {item['domain']} ({item['auction_site']}) - Exp: {item['expiration_date']}")
                
            # Check distinct sites in this batch
            sites = set(item['auction_site'] for item in result.data)
            print(f"\nSites found in this small batch: {sites}")

            # 2. Check for NameSilo/Namecheap specifically in this range
            # Any non-GoDaddy?
            others = [item for item in result.data if item['auction_site'] != 'godaddy']
            if others:
                print(f"\nFound non-GoDaddy items in this range: {len(others)}")
                for o in others:
                     print(f"  {o['domain']} ({o['auction_site']}) - Exp: {o['expiration_date']}")
            else:
                print("\nOnly GoDaddy items found in this sample batch (Expected).")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_filters())
