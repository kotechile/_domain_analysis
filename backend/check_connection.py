import asyncio
import httpx
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

async def test_backend_connectivity():
    print("--- 🚀 Backend Connectivity Diagnostic ---")
    
    # 1. Check local environment variables
    from utils.config import get_settings
    settings = get_settings()
    
    print(f"[*] APP_NAME: {settings.APP_NAME}")
    print(f"[*] SUPABASE_URL: {settings.SUPABASE_URL}")
    print(f"[*] SUPABASE_VERIFY_SSL: {settings.SUPABASE_VERIFY_SSL}")
    
    # 2. Test DNS and HTTP reachable
    print("\n[*] Testing direct HTTP connection to Supabase...")
    try:
        async with httpx.AsyncClient(verify=settings.SUPABASE_VERIFY_SSL) as client:
            resp = await client.get(f"{settings.SUPABASE_URL}/rest/v1/", timeout=5.0)
            print(f"[✓] Successfully reached Supabase. Status: {resp.status_code}")
    except Exception as e:
        print(f"[✗] Failed to reach Supabase: {str(e)}")
    
    # 3. Test Database Client Initialization
    print("\n[*] Initializing Supabase Client...")
    try:
        from services.database import DatabaseService
        db = DatabaseService()
        if db.client:
            print("[✓] Client initialized.")
            # Simple query test
            try:
                # Use a specific table you know exists
                result = db.client.table('auctions').select('count').limit(1).execute()
                print(f"[✓] Database Query Successful. Found Auctions: {len(result.data)}")
            except Exception as query_err:
                 print(f"[!] Query failed (maybe table missing?): {str(query_err)}")
        else:
            print("[✗] Client initialization returned None.")
    except Exception as e:
        print(f"[✗] Fatal error during client init: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_backend_connectivity())
