#!/usr/bin/env python3
"""
Clear the DataForSEO cache for dataforseo.com
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.database import init_database, get_database
from models.domain_analysis import DataSource

async def clear_cache():
    """Clear the cache for dataforseo.com"""
    await init_database()
    db = get_database()
    
    print("Clearing cache for dataforseo.com...")
    
    try:
        # Delete raw data cache
        await db.delete_raw_data("dataforseo.com", DataSource.DATAFORSEO)
        print("✅ DataForSEO cache cleared")
    except Exception as e:
        print(f"❌ Error clearing cache: {e}")
    
    try:
        # Delete Wayback Machine cache
        await db.delete_raw_data("dataforseo.com", DataSource.WAYBACK_MACHINE)
        print("✅ Wayback Machine cache cleared")
    except Exception as e:
        print(f"❌ Error clearing Wayback Machine cache: {e}")

if __name__ == "__main__":
    asyncio.run(clear_cache())








