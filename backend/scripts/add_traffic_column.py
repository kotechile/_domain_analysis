
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from services.database import get_database, init_database

async def migrate():
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
    
    await init_database()
    db = get_database()
    
    print("Adding traffic column to auctions table...")
    
    sql = """
    ALTER TABLE auctions 
    ADD COLUMN IF NOT EXISTS traffic BIGINT;
    
    CREATE INDEX IF NOT EXISTS idx_auctions_traffic ON auctions(traffic);
    """
    
    try:
        # Try to execute via exec_sql RPC if available
        result = db.client.rpc('exec_sql', {'sql': sql}).execute()
        print("Migration executed successfully via exec_sql")
    except Exception as e:
        print(f"RPC exec_sql failed: {e}")
        print("Attempting to use direct SQL via Postgres connection (not implemented in this script)")
        print("Please check if traffic column exists.")

if __name__ == "__main__":
    asyncio.run(migrate())
