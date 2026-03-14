import asyncio
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.database import init_database

async def check_columns():
    db = await init_database()
    
    # Check what's in 'auctions' table first record
    print("Checking 'auctions' table schema via one record...")
    result = db.client.table('auctions').select('*').limit(1).execute()
    
    if result.data:
        print(f"Columns in 'auctions' table: {list(result.data[0].keys())}")
        if 'organic_traffic' in result.data[0]:
            print("✅ 'organic_traffic' column exists")
        else:
            print("❌ 'organic_traffic' column MISSING")
            
        if 'keywords_count' in result.data[0]:
            print("✅ 'keywords_count' column exists")
        else:
            print("❌ 'keywords_count' column MISSING")
    else:
        print("No data in auctions table to check.")

if __name__ == "__main__":
    asyncio.run(check_columns())
