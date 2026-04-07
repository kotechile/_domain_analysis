
import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'backend/src'))

from services.database import init_database, get_database

async def run():
    await init_database()
    db = get_database()
    client = await db._get_client()
    
    # Try to get column info
    query = """
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'auctions'
    """
    
    # Supabase doesn't have a direct query for arbitrary SQL easily via RPC
    # Use existing exec_sql if it exists
    res = await client.rpc('exec_sql', {'sql': query}).execute()
    print(res.data)

if __name__ == "__main__":
    asyncio.run(run())
