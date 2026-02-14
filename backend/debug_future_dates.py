import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def check_future():
    await init_database()
    db = get_database()
    
    print("\n--- CHECKING FUTURE DATES (Feb 9 - Feb 12) ---\n")
    
    try:
        # Check GoDaddy specifically
        query = db.client.table('auctions')\
            .select('*', count='exact')\
            .eq('auction_site', 'godaddy')\
            .gte('expiration_date', '2026-02-09T00:00:00')\
            .lte('expiration_date', '2026-02-12T23:59:59')
            
        res = query.execute()
        print(f"GoDaddy Records in [Feb 9 - Feb 12]: {res.count}")
        
        if res.count > 0:
            print("Sample:")
            for item in res.data[:5]:
                print(f"  {item['domain']}: {item['expiration_date']}")
        else:
            print("No GoDaddy records found in this range.")
            
            # Check what is the MAX expiration date for GoDaddy?
            print("\nChecking MAX expiration date for GoDaddy:")
            max_res = db.client.table('auctions')\
                .select('expiration_date')\
                .eq('auction_site', 'godaddy')\
                .order('expiration_date', desc=True)\
                .limit(1)\
                .execute()
                
            if max_res.data:
                print(f"  Max Expiration: {max_res.data[0]['expiration_date']}")
            else:
                print("  No GoDaddy records found at all?")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_future())
