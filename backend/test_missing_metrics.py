
import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from services.database import get_database, init_database

async def check():
    await init_database()
    db = get_database()
    
    print("--- Testing get_auctions_missing_any_metric_with_filters ---")
    filters = {'scored': True}
    limit = 10
    
    try:
        domains = await db.get_auctions_missing_any_metric_with_filters(filters=filters, limit=limit)
        print(f"Found {len(domains)} domains")
        if domains:
            print(f"Sample domain: {domains[0]['domain']}")
            print(f"Metrics: organic_traffic={domains[0].get('organic_traffic')}, ranking={domains[0].get('ranking')}, backlinks={domains[0].get('backlinks')}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check())
