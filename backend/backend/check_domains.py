import asyncio
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.database import init_database

async def check_domains():
    db = await init_database()
    result = db.client.table('auctions').select('domain').limit(10).execute()
    print(f"Sample domains: {[r['domain'] for r in result.data]}")

if __name__ == "__main__":
    asyncio.run(check_domains())
