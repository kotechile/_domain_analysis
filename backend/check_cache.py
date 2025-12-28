#!/usr/bin/env python3
"""
Check raw data cache for DataForSEO
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.database import init_database, get_database, DataSource

async def check_cache():
    """Check raw data cache"""
    await init_database()
    db = get_database()
    
    print("Checking DataForSEO cache...")
    
    cached_data = await db.get_raw_data('dataforseo.com', DataSource.DATAFORSEO)
    if cached_data:
        print("✅ Cached data found")
        print(f"Keys: {list(cached_data.keys())}")
        
        if 'backlinks_summary' in cached_data:
            backlinks = cached_data['backlinks_summary']
            print(f"Backlinks summary keys: {list(backlinks.keys())}")
            print(f"Total backlinks: {backlinks.get('backlinks')}")
            print(f"Referring domains: {backlinks.get('referring_domains')}")
        else:
            print("❌ No backlinks_summary in cached data")
            
        if 'domain_rank' in cached_data:
            domain_rank = cached_data['domain_rank']
            print(f"Domain rank keys: {list(domain_rank.keys())}")
            if 'organic' in domain_rank:
                organic = domain_rank['organic']
                print(f"Organic ETV: {organic.get('etv')}")
                print(f"Organic count: {organic.get('count')}")
    else:
        print("❌ No cached data found")

if __name__ == "__main__":
    asyncio.run(check_cache())
