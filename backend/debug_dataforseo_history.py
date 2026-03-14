
import asyncio
import os
import sys
import json

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from services.external_apis import DataForSEOService
from utils.config import get_settings
from services.database import init_database

async def main():
    try:
        await init_database()
        service = DataForSEOService()
        domain = "giniloh.com"
        
        print(f"Fetching historical rank overview for {domain}...")
        rank_data = await service.get_historical_rank_overview(domain)
        print(f"Rank Data Result Type: {type(rank_data)}")
        
        if rank_data:
            print("Rank Data Keys:", rank_data.keys())
            items = rank_data.get('items', [])
            print(f"Rank Items Count: {len(items)}")
            if len(items) > 0:
                print(f"First Item Sample: {json.dumps(items[0], indent=2)}")
            else:
                print("Raw Rank Data (sample):")
                print(json.dumps(rank_data, indent=2)[:500])
        
        print(f"Fetching traffic history for {domain}...")
        traffic_data = await service.get_traffic_analytics_history(domain)
        print(f"Traffic Data Result Type: {type(traffic_data)}")
        
        if traffic_data:
            print("Traffic Data Keys:", traffic_data.keys())
            items = traffic_data.get('items', [])
            print(f"Traffic Items Count: {len(items)}")
            if len(items) > 0:
                print(f"First Item Sample: {json.dumps(items[0], indent=2)}")
            else:
                print("Raw Traffic Data (sample):")
                print(json.dumps(traffic_data, indent=2)[:500])

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
