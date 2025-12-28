#!/usr/bin/env python3
"""
Test DataForSEO parsing with real cached data
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.database import init_database, get_database, DataSource
from services.external_apis import DataForSEOService

async def test_parsing():
    """Test DataForSEO parsing with real cached data"""
    await init_database()
    
    print("Testing DataForSEO parsing with cached data...")
    
    # Get the cached data
    db = get_database()
    cached_data = await db.get_raw_data('dataforseo.com', DataSource.DATAFORSEO)
    
    if not cached_data:
        print("❌ No cached data found")
        return
    
    print("✅ Cached data found")
    print(f"Backlinks summary: {cached_data.get('backlinks_summary', {}).get('backlinks')}")
    print(f"Referring domains: {cached_data.get('backlinks_summary', {}).get('referring_domains')}")
    
    # Test parsing
    dataforseo_service = DataForSEOService()
    parsed_metrics = dataforseo_service.parse_domain_metrics(cached_data)
    
    print(f"\nParsed metrics:")
    print(f"Total backlinks: {parsed_metrics.total_backlinks}")
    print(f"Total referring domains: {parsed_metrics.total_referring_domains}")
    print(f"Organic traffic est: {parsed_metrics.organic_traffic_est}")
    print(f"Total keywords: {parsed_metrics.total_keywords}")

if __name__ == "__main__":
    asyncio.run(test_parsing())
