import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def check_source_data():
    await init_database()
    db = get_database()
    
    print("\n--- CHECKING GODADDY SOURCE DATA ---\n")
    
    try:
        # Fetch a few GoDaddy records to see if source_data has clues
        res = db.client.table('auctions')\
            .select('domain, expiration_date, source_data')\
            .eq('auction_site', 'godaddy')\
            .limit(5)\
            .execute()
            
        if not res.data:
            print("No GoDaddy records found.")
            return

        for item in res.data:
            print(f"Domain: {item.get('domain')}")
            print(f"Expiration: {item.get('expiration_date')}")
            
            # Print keys of source_data to see if there's any file info
            source_data = item.get('source_data', {})
            print(f"Source Data Keys: {list(source_data.keys())}")
            
            # Check for specific keys that might indicate "tomorrow"
            # GoDaddy JSON usually has 'auctionEndTime'. Let's see if it matches expiration.
            auction_end = source_data.get('auctionEndTime')
            print(f"Source Auction End Time: {auction_end}")
            
            print("-" * 30)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_source_data())
