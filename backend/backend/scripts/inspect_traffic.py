
import asyncio
import os
import sys
from dotenv import load_dotenv
import json

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from services.database import get_database, init_database

async def inspect():
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
    
    await init_database()
    db = get_database()
    
    print("Searching for auctions with ANY page_statistics...")
    response = db.client.table('auctions').select('*').eq('has_statistics', True).limit(20).execute()
    
    if not response.data:
        print("No auctions with statistics found.")
        return
        
    print(f"Found {len(response.data)} records. Checking for traffic keys...")
    if len(response.data) > 0:
        print("Sample Auction Columns:", list(response.data[0].keys()))
    
    found_traffic = False
    for auction in response.data:
        stats = auction.get('page_statistics') or {}
        keys = list(stats.keys())
        
        # Check for any traffic-related keys
        traffic_keys = [k for k in keys if 'traffic' in k.lower() or 'etv' in k.lower()]
        
        if traffic_keys or 'metrics' in keys:
            print(f"\nDomain: {auction.get('domain')}")
            print(f"Keys found: {keys}")
            if traffic_keys:
                print(f"Traffic keys: {traffic_keys}")
                for k in traffic_keys:
                    print(f"  {k}: {stats[k]}")
            
            if 'metrics' in stats:
                print(f"  metrics: {json.dumps(stats['metrics'], indent=2)}")
            found_traffic = True

    if not found_traffic:
        print("\nNo traffic data found in the sample of 20 records.")
        print("Sample keys from first record:", list(response.data[0].get('page_statistics', {}).keys()))

if __name__ == "__main__":
    asyncio.run(inspect())
