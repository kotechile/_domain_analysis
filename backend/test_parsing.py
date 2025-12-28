#!/usr/bin/env python3
"""
Test script to verify DataForSEO parsing logic
"""

import asyncio
import json
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.database import init_database
from services.external_apis import DataForSEOService

async def test_parsing():
    """Test the DataForSEO parsing logic with sample data"""
    await init_database()
    
    # Sample data from the API response
    sample_data = {
        "domain_rank": {
            "organic": {
                "count": 1000,
                "etv": 5000
            }
        },
        "backlinks_summary": {
            "backlinks": 1953868,
            "referring_domains": 2485
        },
        "backlinks": {},
        "keywords": {}
    }
    
    service = DataForSEOService()
    metrics = service.parse_domain_metrics(sample_data)
    
    print("Parsed metrics:")
    print(f"Total backlinks: {metrics.total_backlinks}")
    print(f"Total referring domains: {metrics.total_referring_domains}")
    print(f"Organic traffic est: {metrics.organic_traffic_est}")
    print(f"Total keywords: {metrics.total_keywords}")

if __name__ == "__main__":
    asyncio.run(test_parsing())
