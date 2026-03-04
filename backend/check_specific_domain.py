import asyncio
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.database import init_database

async def check_specific_domain(domain):
    db = await init_database()
    result = db.client.table('auctions').select('domain, organic_traffic, updated_at, page_statistics').eq('domain', domain).execute()
    print(f"Domain {domain}: {result.data}")

if __name__ == "__main__":
    domain = sys.argv[1] if len(sys.argv) > 1 else 'frlengendsapp.com'
    asyncio.run(check_specific_domain(domain))
