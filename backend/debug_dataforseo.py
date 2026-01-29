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
    
    import httpx
    import json
    from datetime import datetime, timedelta

    creds['api_url'] = "https://api.dataforseo.com/v3" # Force correct URL
    print(f"✅ Using API URL: {creds['api_url']}")
    
    domain = 'webflow.com'
    url = f"{creds['api_url']}/dataforseo_labs/google/historical_rank_overview/live"
    
    end_date = datetime.utcnow() - timedelta(days=7)
    start_date = end_date - timedelta(days=365*4)
    
    post_data = [{
        "target": domain,
        "language_name": "English",
        "location_code": 2840,
        "date_from": start_date.strftime("%Y-%m-%d"),
        "date_to": end_date.strftime("%Y-%m-%d")
    }]
    
    print(f"Please wait, calling: {url}")
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            url,
            auth=(creds['login'], creds['password']),
            json=post_data
        )
        print(f"Status: {response.status_code}")
        try:
            data = response.json()
            print(json.dumps(data, indent=2))
            if data.get("status_code") == 20000:
                print("✅ Status code 20000 (Success)")
                if data.get("tasks"):
                    res = data["tasks"][0].get("result")
                    if res:
                        print(f"✅ Result found with {len(res)} items")
                    else:
                        print("❌ Result is empty")
                else:
                    print("❌ No tasks in response")
            else:
                print(f"❌ API Status Code: {data.get('status_code')}")
                print(f"Message: {data.get('status_message')}")
        except Exception as e:
            print(f"Failed to parse JSON: {e}")
            print(response.text[:500])

if __name__ == "__main__":
    asyncio.run(debug_dataforseo())








