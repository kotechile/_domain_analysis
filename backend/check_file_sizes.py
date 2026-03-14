import asyncio
import httpx
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.database import get_database, init_database

async def check_file_sizes():
    await init_database()
    db = get_database()
    
    files = [
        ("listingfiles", "godaddy_tomorrow.json"),
        ("listingfiles", "godaddy_today.json"),
        ("listingfiles", "Namecheap_Market_Sales.csv"),
        ("listingfiles", "Namecheap_Market_Sales_Buy_Now.csv")
    ]
    
    service_role_key = db.settings.SUPABASE_SERVICE_ROLE_KEY or db.settings.SUPABASE_KEY
    
    print("\n=== Checking File Sizes in Supabase Storage ===\n")
    
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        for bucket, path in files:
            storage_url = f"{db.settings.SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
            try:
                # Use HEAD request to get headers only
                response = await client.head(
                    storage_url,
                    headers={
                        "Authorization": f"Bearer {service_role_key}",
                        "apikey": service_role_key
                    }
                )
                
                if response.status_code == 200:
                    size = int(response.headers.get("Content-Length", 0))
                    print(f"File: {path}")
                    print(f"  Size: {size / (1024 * 1024):.2f} MB")
                else:
                    print(f"File: {path}")
                    print(f"  Error: HTTP {response.status_code}")
            except Exception as e:
                print(f"File: {path}")
                print(f"  Error: {str(e)}")
            print("-" * 30)

if __name__ == "__main__":
    asyncio.run(check_file_sizes())
