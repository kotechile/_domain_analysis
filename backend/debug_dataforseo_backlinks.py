#!/usr/bin/env python3
"""
Debug DataForSEO backlinks summary API call
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.database import init_database, get_database
from services.external_apis import DataForSEOService

async def debug_backlinks():
    """Debug DataForSEO backlinks summary API call"""
    await init_database()
    
    print("Testing DataForSEO backlinks summary API call...")
    
    # Test credentials
    from services.secrets_service import get_secrets_service
    secrets = get_secrets_service()
    creds = await secrets.get_dataforseo_credentials()
    
    if not creds:
        print("❌ No DataForSEO credentials found")
        return
    
    print(f"✅ Credentials loaded: {creds['api_url']}")
    print(f"Login: {creds['login']}")
    print(f"Password: {'*' * len(creds['password'])}")
    
    # Test direct API call
    import httpx
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test backlinks summary endpoint
        post_data = {}
        post_data[len(post_data)] = {
            "target": "dataforseo.com",
            "internal_list_limit": 10,
            "include_subdomains": True,
            "backlinks_filters": ["dofollow", "=", True],
            "backlinks_status_type": "all"
        }
        
        url = f"{creds['api_url']}/backlinks/summary/live"
        print(f"\nTesting URL: {url}")
        print(f"Post data: {post_data}")
        
        try:
            response = await client.post(
                url,
                auth=(creds['login'], creds['password']),
                json=post_data
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response data keys: {list(data.keys())}")
                print(f"Status code in response: {data.get('status_code')}")
                print(f"Status message: {data.get('status_message')}")
                
                if data.get('tasks'):
                    task = data['tasks'][0]
                    print(f"Task status: {task.get('status_code')}")
                    print(f"Task message: {task.get('status_message')}")
                    if task.get('result'):
                        print(f"Result keys: {list(task['result'][0].keys()) if task['result'] else 'No result'}")
            else:
                print(f"Error response: {response.text}")
                
        except Exception as e:
            print(f"❌ API call failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_backlinks())
