import asyncio
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from services.database import DatabaseService

load_dotenv()

async def run():
    db = DatabaseService()
    client = await db._get_client()
    sql = """
    SELECT prosrc, l.lanname 
    FROM pg_proc p JOIN pg_language l ON p.prolang = l.oid 
    WHERE proname = 'exec_sql'
    """
    try:
        res = await client.rpc('exec_sql', {'sql': sql}).execute()
        print(f"exec_sql definition: {res.data}")
    except Exception as e:
        print(f"Listing functions FAILED: {str(e)}")
        
    try:
        # Test an INSERT without ON CONFLICT first (to verify basics)
        sql = "SELECT domain FROM auctions LIMIT 1"
        res = await client.rpc('exec_sql', {'sql': sql}).execute()
        print(f"SELECT result: {res.data}")
    except Exception as e:
        print(f"SELECT FAILED: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run())
