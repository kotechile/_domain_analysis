import asyncio
import os
import sys
import json
from datetime import datetime, timezone

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.database import init_database

async def check_full_data():
    db = await init_database()
    
    # Get 5 most recently updated auctions with full stats
    result = db.client.table('auctions').select('domain,organic_traffic,page_statistics,updated_at').order('updated_at', desc=True).limit(5).execute()
    
    if result.data:
        for item in result.data:
            print(f"Domain: {item['domain']}")
            print(f"  Organic Traffic (top-level): {item['organic_traffic']}")
            print(f"  Page Statistics: {json.dumps(item['page_statistics'] if item['page_statistics'] else {}, indent=2)}")
            print(f"  Updated at: {item['updated_at']}")
            print("-" * 20)
    else:
        print("No recently updated auctions found.")

if __name__ == "__main__":
    asyncio.run(check_full_data())
