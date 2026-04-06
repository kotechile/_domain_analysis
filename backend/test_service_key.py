import httpx
import os
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv("SUPABASE_URL", "https://sbdomain.buildomain.com")
# Use the service role key for basic querying to test its validity
KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

async def check():
    headers = {
        "apikey": KEY,
        "Authorization": f"Bearer {KEY}"
    }
    
    async with httpx.AsyncClient(verify=False) as client:
        print(f"\n--- Checking {URL} with key {KEY[:10]}... ---")
        res = await client.get(f"{URL}/rest/v1/auctions?limit=1", headers=headers)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            print("SERVICE_ROLE_KEY is VALID!")
            print(json.dumps(res.json(), indent=2))
        else:
            print(f"SERVICE_ROLE_KEY is INVALID: {res.text}")

if __name__ == "__main__":
    asyncio.run(check())
