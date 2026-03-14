import httpx
import asyncio
import os
import sys
import json
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.database import init_database
from services.secrets_service import get_secrets_service

async def test_dataforseo_traffic():
    # Load env
    load_dotenv()
    
    # Init DB (needed for secrets service)
    await init_database()
    
    secrets_service = get_secrets_service()
    credentials = await secrets_service.get_dataforseo_credentials()
    
    if not credentials:
        print("DataForSEO credentials not found in database")
        return

    auth = (credentials['login'], credentials['password'])
    print(f"Using login: {credentials['login']}")
    
    # Test URL
    url = "https://api.dataforseo.com/v3/dataforseo_labs/google/bulk_traffic_estimation/live"
    
    payload = [{
        "targets": ["google.com", "amazon.com"],
        "location_code": 2840,
        "language_code": "en"
    }]
    
    print(f"Testing POST to {url}...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload, auth=auth)
            print(f"Status Code: {response.status_code}")
            try:
                print(f"Response Body: {json.dumps(response.json(), indent=2)}")
            except:
                print(f"Response Body (not JSON): {response.text}")
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_dataforseo_traffic())
