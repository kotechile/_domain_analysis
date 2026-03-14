import asyncio
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.database import init_database

async def add_missing_columns():
    db = await init_database()
    
    print("Attempting to add missing columns using exec_sql RPC...")
    
    sql = """
    ALTER TABLE auctions ADD COLUMN IF NOT EXISTS keywords_count INTEGER;
    ALTER TABLE auctions ADD COLUMN IF NOT EXISTS organic_traffic BIGINT;
    
    -- Also ensure organic_traffic is BIGINT just in case it was something else
    -- ALTER TABLE auctions ALTER COLUMN organic_traffic TYPE BIGINT USING organic_traffic::BIGINT;
    """
    
    try:
        result = db.client.rpc('exec_sql', {'sql': sql}).execute()
        print(f"Success! Result: {result.data}")
    except Exception as e:
        print(f"Failed to run exec_sql: {e}")
        print("\nPlease run this SQL manually in your Supabase SQL Editor:")
        print("-" * 50)
        print("ALTER TABLE auctions ADD COLUMN IF NOT EXISTS keywords_count INTEGER;")
        print("ALTER TABLE auctions ADD COLUMN IF NOT EXISTS organic_traffic BIGINT;")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(add_missing_columns())
