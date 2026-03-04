import asyncio
import os
import sys
from datetime import datetime, timezone

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.database import init_database

async def check_recent_updates():
    db = await init_database()
    
    # Get 10 most recently updated auctions
    result = db.client.table('auctions').select('domain,organic_traffic,page_statistics,updated_at').order('updated_at', desc=True).limit(10).execute()
    
    if result.data:
        print(f"Recent updates (found {len(result.data)} items):")
        for item in result.data:
            print(f"Domain: {item['domain']}")
            print(f"  Traffic: {item['organic_traffic']}")
            print(f"  Updated at: {item['updated_at']}")
            # print(f"  Stats: {item['page_statistics']}")
    else:
        print("No recently updated auctions found.")

if __name__ == "__main__":
    asyncio.run(check_recent_updates())
