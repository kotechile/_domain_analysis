import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def check_dates():
    await init_database()
    db = get_database()
    
    print("\n--- CHECKING EXPIRATION DATES ---\n")
    
    try:
        # 1. Check GoDaddy Date Range
        print("Querying GoDaddy Date Range...")
        gd_min = db.client.table('auctions').select('expiration_date').eq('auction_site', 'godaddy').order('expiration_date', desc=False).limit(1).execute()
        gd_max = db.client.table('auctions').select('expiration_date').eq('auction_site', 'godaddy').order('expiration_date', desc=True).limit(1).execute()
        
        min_date = gd_min.data[0]['expiration_date'] if gd_min.data else "None"
        max_date = gd_max.data[0]['expiration_date'] if gd_max.data else "None"
        print(f"GoDaddy Range: {min_date} to {max_date}")

        # 2. Check counts for the User's specific filter (Feb 9 2026 - Feb 28 2026)
        # Note: timestamps in DB might include time, so we need to be careful.
        # Screenshot has 2026.
        start_date = "2026-02-09T00:00:00"
        end_date = "2026-02-28T23:59:59"
        
        print(f"\nChecking range: {start_date} to {end_date}")
        
        range_count = db.client.table('auctions')\
            .select('*', count='exact')\
            .gte('expiration_date', start_date)\
            .lte('expiration_date', end_date)\
            .limit(1)\
            .execute()
            
        print(f"Records in User's Filter Range: {range_count.count}")
        
        # 3. Check "Buy Now" dates (Namecheap/Namesilo)
        print("\nChecking Buy Now (2099) counts...")
        future_count = db.client.table('auctions')\
            .select('*', count='exact')\
            .gt('expiration_date', '2090-01-01')\
            .limit(1)\
            .execute()
            
        print(f"Records with date > 2090 (Buy Now): {future_count.count}")
        
        # 4. Check 'Today' / 'Tomorrow' relative to now
        now = datetime.utcnow().isoformat()
        print(f"\nCurrent UTC Time: {now}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_dates())
