#!/usr/bin/env python3
"""
Test script to call DataForSEO API directly and see the response structure
"""

import asyncio
import json
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.database import init_database
from services.external_apis import DataForSEOService

async def test_dataforseo_api():
    """Test DataForSEO API calls directly"""
    await init_database()
    
    service = DataForSEOService()
    
    print("Testing DataForSEO API calls...")
    
    # Test backlinks summary
    print("\n1. Testing backlinks summary...")
    backlinks_summary = await service.get_backlinks_summary("dataforseo.com")
    if backlinks_summary:
        print(f"Backlinks summary keys: {list(backlinks_summary.keys())}")
        print(f"Backlinks: {backlinks_summary.get('backlinks', 'N/A')}")
        print(f"Referring domains: {backlinks_summary.get('referring_domains', 'N/A')}")
    else:
        print("No backlinks summary data")
    
    # Test domain analytics
    print("\n2. Testing domain analytics...")
    domain_analytics = await service.get_domain_analytics("dataforseo.com")
    if domain_analytics:
        print(f"Domain analytics keys: {list(domain_analytics.keys())}")
        print(f"Backlinks summary in analytics: {domain_analytics.get('backlinks_summary', {})}")
        print(f"Domain rank in analytics: {domain_analytics.get('domain_rank', {})}")
    else:
        print("No domain analytics data")

if __name__ == "__main__":
    asyncio.run(test_dataforseo_api())