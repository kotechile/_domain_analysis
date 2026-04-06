import httpx
import os
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()

# We need the SERVICE ROLE KEY because anon can't run RPC calls (usually)
URL = os.getenv("SUPABASE_URL", "https://sbdomain.buildomain.com")
# Try to get the service role key from .env if it's there
KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

async def run_sql(sql):
    headers = {
        "apikey": KEY,
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(verify=False) as client:
        # Try both RPC names often used: 'exec_sql' and 'query'
        for rpc_name in ['exec_sql', 'query']:
            print(f"Trying RPC {rpc_name}...")
            endpoint = f"{URL}/rest/v1/rpc/{rpc_name}"
            payload = {"sql": sql}
            
            res = await client.post(endpoint, headers=headers, json=payload)
            print(f"Status: {res.status_code}")
            print(f"Response: {res.text}")
            if res.status_code == 200:
                print(f"SUCCESS with {rpc_name}!")
                return True
        return False

if __name__ == "__main__":
    asyncio.run(run_sql("SELECT 1;"))
