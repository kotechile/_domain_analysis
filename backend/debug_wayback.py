#!/usr/bin/env python3
"""
Debug Wayback Machine API calls
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.database import init_database, get_database, DataSource
from services.external_apis import WaybackMachineService

async def debug_wayback():
    """Debug Wayback Machine API calls"""
    await init_database()
    
    print("Testing Wayback Machine API calls...")
    
    # Test credentials
    from services.secrets_service import get_secrets_service
    secrets = get_secrets_service()
    wayback_config = await secrets.get_wayback_machine_config()
    
    print(f"✅ Wayback Machine config: {wayback_config}")
    
    # Test API call
    wayback_service = WaybackMachineService()
    
    print("\nTesting get_domain_history...")
    try:
        data = await wayback_service.get_domain_history('dataforseo.com')
        if data:
            print("✅ Wayback Machine API call successful")
            print(f"Keys in response: {list(data.keys())}")
            print(f"Total captures: {data.get('total_captures')}")
            print(f"First capture year: {data.get('first_capture_year')}")
            print(f"Last capture date: {data.get('last_capture_date')}")
        else:
            print("❌ Wayback Machine API call returned None")
    except Exception as e:
        print(f"❌ Wayback Machine API call failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_wayback())
