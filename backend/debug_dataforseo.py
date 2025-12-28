#!/usr/bin/env python3
"""
Debug DataForSEO API calls
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.database import init_database, get_database
from services.external_apis import DataForSEOService

async def debug_dataforseo():
    """Debug DataForSEO API calls"""
    await init_database()
    
    print("Testing DataForSEO API calls...")
    
    # Test credentials
    from services.secrets_service import get_secrets_service
    secrets = get_secrets_service()
    creds = await secrets.get_dataforseo_credentials()
    
    if not creds:
        print("❌ No DataForSEO credentials found")
        return
    
    print(f"✅ Credentials loaded: {creds['api_url']}")
    
    # Test API call
    dataforseo_service = DataForSEOService()
    
    print("\nTesting get_domain_analytics...")
    try:
        data = await dataforseo_service.get_domain_analytics('dataforseo.com')
        if data:
            print("✅ API call successful")
            print(f"Keys in response: {list(data.keys())}")
            
            # Check specific data
            if 'domain_rank' in data:
                print(f"Domain rank data: {data['domain_rank']}")
            else:
                print("❌ No domain_rank data")
                
            if 'backlinks_summary' in data:
                print(f"Backlinks summary: {data['backlinks_summary']}")
            else:
                print("❌ No backlinks_summary data")
        else:
            print("❌ API call returned None")
    except Exception as e:
        print(f"❌ API call failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_dataforseo())








