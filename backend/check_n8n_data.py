#!/usr/bin/env python3
"""
Diagnostic script to check if N8N webhook data is in the database
and if the analysis service polling would find it.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database
from models.domain_analysis import DataSource, DetailedDataType

async def check_n8n_data(domain: str):
    """Check if N8N data exists in database"""
    await init_database()
    db = get_database()
    
    print(f"\n=== Checking N8N Data for {domain} ===\n")
    
    # Check summary data
    print("1. Checking Summary Data (raw_data):")
    print("   Query: get_raw_data(domain, DataSource.DATAFORSEO)")
    raw_data = await db.get_raw_data(domain, DataSource.DATAFORSEO)
    if raw_data:
        print(f"   ✅ Found raw_data")
        if "backlinks_summary" in raw_data:
            summary = raw_data["backlinks_summary"]
            print(f"   ✅ Found backlinks_summary key")
            print(f"      - backlinks: {summary.get('backlinks', 'N/A')}")
            print(f"      - referring_domains: {summary.get('referring_domains', 'N/A')}")
            print(f"      - rank: {summary.get('rank', 'N/A')}")
        else:
            print(f"   ❌ backlinks_summary key NOT found")
            print(f"      Available keys: {list(raw_data.keys())}")
    else:
        print(f"   ❌ No raw_data found")
    
    print("\n2. Checking Detailed Data (detailed_data):")
    print("   Query: get_detailed_data(domain, DetailedDataType.BACKLINKS)")
    detailed_data = await db.get_detailed_data(domain, DetailedDataType.BACKLINKS)
    if detailed_data:
        print(f"   ✅ Found detailed_data")
        json_data = detailed_data.json_data
        if isinstance(json_data, dict):
            items = json_data.get("items", [])
            print(f"   ✅ Found items array with {len(items)} items")
            print(f"      - total_count: {json_data.get('total_count', 'N/A')}")
            print(f"      - items_count: {json_data.get('items_count', 'N/A')}")
            if items:
                print(f"      - First item keys: {list(items[0].keys())[:5]}...")
        else:
            print(f"   ⚠️  json_data is not a dict: {type(json_data)}")
    else:
        print(f"   ❌ No detailed_data found")
    
    print("\n3. Analysis Service Polling Check:")
    print("   Summary polling looks for: cached_data.get('backlinks_summary')")
    if raw_data and raw_data.get("backlinks_summary"):
        print("   ✅ Summary data would be found by polling")
    else:
        print("   ❌ Summary data would NOT be found by polling")
    
    print("   Detailed polling looks for: get_detailed_data(domain, DetailedDataType.BACKLINKS)")
    if detailed_data:
        print("   ✅ Detailed data would be found by polling")
    else:
        print("   ❌ Detailed data would NOT be found by polling")
    
    print("\n=== Check Complete ===\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_n8n_data.py <domain>")
        print("Example: python check_n8n_data.py giniloh.com")
        sys.exit(1)
    
    domain = sys.argv[1]
    asyncio.run(check_n8n_data(domain))

















