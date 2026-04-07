
import asyncio
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

async def test_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    print(f"URL: {url}")
    print(f"Key Prefix: {key[:10]}...")
    
    try:
        client = create_client(url, key)
        # Try to select from a public table
        res = client.table("auctions").select("count").limit(1).execute()
        print(f"Public Client Success: {res.data}")
    except Exception as e:
        print(f"Public Client Failed: {str(e)}")
        
    try:
        client_admin = create_client(url, service_key)
        res = client_admin.table("auctions").select("count").limit(1).execute()
        print(f"Admin Client Success: {res.data}")
    except Exception as e:
        print(f"Admin Client Failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_supabase())
