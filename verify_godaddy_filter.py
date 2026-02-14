import asyncio
import sys
import os
from pprint import pprint
from dotenv import load_dotenv

# Load env vars
load_dotenv("backend/.env")

# Add backend/src to path
sys.path.append(os.path.abspath("backend/src"))

from services.auctions_service import AuctionsService
from services.database import get_database, init_database

async def verify_godaddy():
    # Initialize DB first
    await init_database()
    
    service = AuctionsService()
    db = get_database()
    
    print("--- Verifying GoDaddy Data ---")
    
    # 1. Check if there are ANY GoDaddy auctions in DB (case insensitive check via Python if needed, but SQL is better)
    # We can't run raw SQL easily without client.rpc or similar, but let's try to fetch SOME auctions and check sites.
    
    print("Fetching sample of 100 auctions to list sites...")
    sample = await db.get_auctions_with_statistics(limit=100)
    sites = set(a['auction_site'] for a in sample.get('auctions', []))
    print(f"Found sites in sample: {sites}")
    
    # 2. Check get_auctions_report with 'godaddy' filter
    print("\nFetching with auction_sites=['godaddy']...")
    report = await service.get_auctions_report(
        filters={'auction_sites': ['godaddy']},
        limit=10
    )
    
    count = report.get('count', 0)
    print(f"Count with ['godaddy']: {count}")
    if count > 0:
        print("First result site:", report['auctions'][0]['auction_site'])
        print("Sample expiration dates:")
        for a in report['auctions'][:5]:
            print(f" - {a['domain']}: {a['expiration_date']}")
    
    # 3. Check with 'GoDaddy' (mixed case) just in case
    print("\nFetching with auction_sites=['GoDaddy']...")
    report_mixed = await service.get_auctions_report(
        filters={'auction_sites': ['GoDaddy']},
        limit=10
    )
    print(f"Count with ['GoDaddy']: {report_mixed.get('count', 0)}")

if __name__ == "__main__":
    asyncio.run(verify_godaddy())
