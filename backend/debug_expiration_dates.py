
import asyncio
import os
import sys

# Add backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend', 'src'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

from services.database import DatabaseService

async def check_dates():
    db = DatabaseService()
    print("Checking upcoming auctions...")
    
    print("Checking with filters: gte 2026-02-02, lte 2026-02-02T23:59:59")
    res = db.client.table('auctions') \
        .select('domain, expiration_date') \
        .gte('expiration_date', '2026-02-02') \
        .lte('expiration_date', '2026-02-02T23:59:59') \
        .order('expiration_date') \
        .limit(20) \
        .execute()
        
    print(f"Found {len(res.data)} auctions:")
    for row in res.data:
        print(f"Domain: {row['domain']}, Expires: {row['expiration_date']}")

if __name__ == "__main__":
    asyncio.run(check_dates())
