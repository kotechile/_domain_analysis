
import asyncio
import os
import sys

# Add backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend', 'src'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

from services.database import DatabaseService
from services.auctions_service import AuctionsService

async def reproduce():
    db = DatabaseService()
    filters = {
        'expiration_from_date': '2026-02-02',
        'expiration_to_date': '2026-02-02' 
    }
    
    print(f"Testing filters: {filters}")
    
    result = await db.get_auctions_with_statistics(
        filters=filters,
        limit=5
    )
    
    print(f"Total Count: {result.get('total_count')}")
    print(f"Returned: {len(result.get('auctions', []))}")
    for a in result.get('auctions', []):
        print(f"Domain: {a['domain']}, Exp: {a['expiration_date']}")

if __name__ == "__main__":
    asyncio.run(reproduce())
