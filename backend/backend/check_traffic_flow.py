import asyncio
import os
import sys
import json
from datetime import datetime, timezone

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.database import init_database

async def check_traffic_v2():
    db = await init_database()
    
    # Simple check for any traffic data
    # We'll fetch all and filter in python to avoid PostgREST quirks with nulls
    print("Checking for auctions with traffic data...")
    result = db.client.table('auctions').select('domain,organic_traffic,updated_at').limit(1000).execute()
    
    traffic_found = [item for item in result.data if item.get('organic_traffic') is not None and item.get('organic_traffic') > 0]
    
    if traffic_found:
        print(f"Found {len(traffic_found)} auctions with non-zero traffic:")
        for item in sorted(traffic_found, key=lambda x: x['updated_at'], reverse=True)[:10]:
            print(f"Domain: {item['domain']}")
            print(f"  Traffic: {item['organic_traffic']}")
            print(f"  Updated at: {item['updated_at']}")
    else:
        # Check if anything was updated in the last hour
        recently_updated = [item for item in result.data if item.get('updated_at')]
        print("\nNo traffic found. Checking recently updated items...")
        for item in sorted(recently_updated, key=lambda x: x['updated_at'], reverse=True)[:5]:
             print(f"Domain: {item['domain']} | Updated: {item['updated_at']} | Traffic: {item['organic_traffic']}")

if __name__ == "__main__":
    asyncio.run(check_traffic_v2())
