#!/usr/bin/env python3
"""
Test DataForSEO parsing with real data
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.database import init_database, get_database, DataSource
from services.external_apis import DataForSEOService

async def test_parsing():
    """Test DataForSEO parsing with real data"""
    await init_database()
    
    print("Testing DataForSEO parsing...")
    
    # Get the cached data
    db = get_database()
    cached_data = await db.get_raw_data('dataforseo.com', DataSource.DATAFORSEO)
    
    if not cached_data:
        print("❌ No cached data found")
        return
    
    print("✅ Cached data found")
    print(f"Keys: {list(cached_data.keys())}")
    
    # Test parsing
    dataforseo_service = DataForSEOService()
    parsed_metrics = dataforseo_service.parse_domain_metrics(cached_data)
    
    print(f"\nParsed metrics:")
    print(f"Total backlinks: {parsed_metrics.total_backlinks}")
    print(f"Total referring domains: {parsed_metrics.total_referring_domains}")
    print(f"Organic traffic est: {parsed_metrics.organic_traffic_est}")
    print(f"Total keywords: {parsed_metrics.total_keywords}")
    
    if parsed_metrics.organic_metrics:
        print(f"Organic metrics ETV: {parsed_metrics.organic_metrics.etv}")
        print(f"Organic metrics count: {parsed_metrics.organic_metrics.count}")
    else:
        print("❌ No organic metrics")

if __name__ == "__main__":
    asyncio.run(test_parsing())
