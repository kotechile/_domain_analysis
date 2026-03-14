import asyncio
import os
import sys
import json
from datetime import datetime, timezone

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.database import init_database

async def check_any_traffic():
    db = await init_database()
    
    # Get auctions with non-null organic_traffic
    result = db.client.table('auctions').select('domain,organic_traffic,page_statistics,updated_at').neq('organic_traffic', 'null').limit(10).execute()
    
    if result.data:
        print(f"Found {len(result.data)} auctions with traffic:")
        for item in result.data:
            print(f"Domain: {item['domain']}")
            print(f"  Traffic: {item['organic_traffic']}")
            print(f"  Updated at: {item['updated_at']}")
    else:
        print("No auctions with traffic found.")

    # Also check for auctions where page_statistics is not empty
    result = db.client.table('auctions').select('domain,organic_traffic,page_statistics,updated_at').neq('page_statistics', '{}').limit(10).execute()
    if result.data:
        print(f"\nFound {len(result.data)} auctions with non-empty page_statistics:")
        for item in result.data:
            print(f"Domain: {item['domain']}")
            print(f"  Traffic: {item['organic_traffic']}")
            print(f"  Stats Keys: {list(item['page_statistics'].keys())}")
            print(f"  Updated at: {item['updated_at']}")
    else:
        print("\nNo auctions with non-empty page_statistics found.")

if __name__ == "__main__":
    asyncio.run(check_any_traffic())
