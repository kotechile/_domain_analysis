import asyncio
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "backend/src"))

from services.database import DatabaseService

async def check():
    load_dotenv("backend/.env")
    db = DatabaseService()
    client = await db._get_client()
    
    # Check auctions columns
    res = await client.table('auctions').select('*').limit(1).execute()
    if res.data:
        print(f"Auctions row keys: {list(res.data[0].keys())}")
        print(f"Auctions sample row: {res.data[0]}")
    else:
        print("Auctions table is empty")

if __name__ == "__main__":
    asyncio.run(check())
