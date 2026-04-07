
import asyncio
import os
import sys
from typing import Optional

# Add the backend src to path
sys.path.append(os.path.join(os.getcwd(), 'backend', 'src'))

from services.database import DatabaseService

async def check_columns():
    db = DatabaseService()
    client = await db._get_client()
    
    # Check one row from auctions
    res = await client.table('auctions').select('*').limit(1).execute()
    if res.data:
        print(f"Columns in auctions: {list(res.data[0].keys())}")
    else:
        print("No rows found in auctions")

if __name__ == "__main__":
    asyncio.run(check_columns())
