#!/usr/bin/env python3
"""
Debug the exact API calls being made
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.database import init_database, get_database
from services.secrets_service import get_secrets_service

async def debug_api():
    """Debug the API calls"""
    await init_database()
    secrets_service = get_secrets_service()
    
    # Get credentials
    credentials = await secrets_service.get_dataforseo_credentials()
    print(f"Credentials: {credentials}")
    
    if credentials:
        import httpx
        
        # Test the exact API call
        async with httpx.AsyncClient(timeout=30.0) as client:
            post_data = {}
            post_data[len(post_data)] = {
                "target": "dataforseo.com",
                "internal_list_limit": 10,
                "include_subdomains": True,
                "backlinks_filters": ["dofollow", "=", True],
                "backlinks_status_type": "all"
            }
            
            url = f"{credentials['api_url']}/backlinks/summary/live"
            print(f"Making request to: {url}")
            print(f"Post data: {post_data}")
            
            response = await client.post(
                url,
                auth=(credentials['login'], credentials['password']),
                json=post_data
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            print(f"Response body: {response.text[:500]}...")

if __name__ == "__main__":
    asyncio.run(debug_api())








