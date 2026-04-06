import httpx
import os
import json
from dotenv import load_dotenv

load_dotenv()

URL = "https://sbdomain.buildomain.com"
KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzdXBhYmFzZSIsImlhdCI6MTc3MzUxNzI2MCwiZXhwIjo0OTI5MTkwODYwLCJyb2xlIjoiYW5vbiJ9.zxcfAdU3YO-jb8SOsCSbzBfrf4uD6L-v5v6valikHTE"

async def check():
    headers = {
        "apikey": KEY,
        "Authorization": f"Bearer {KEY}"
    }
    
    async with httpx.AsyncClient(verify=False) as client:
        # Get auctions schema
        print("\n--- Auctions Table Data ---")
        res = await client.get(f"{URL}/rest/v1/auctions?limit=2", headers=headers)
        if res.status_code == 200:
            print(json.dumps(res.json(), indent=2))
        else:
            print(f"Failed to get auctions: {res.status_code} {res.text}")

        # Get staging schema
        print("\n--- Staging Table 0 Data ---")
        res = await client.get(f"{URL}/rest/v1/auctions_staging_0?limit=2", headers=headers)
        if res.status_code == 200:
            print(json.dumps(res.json(), indent=2))
        else:
            print(f"Failed to get staging_0: {res.status_code} {res.text}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(check())
