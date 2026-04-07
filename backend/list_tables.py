
import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.database import init_database, get_database

async def run():
    await init_database()
    db = get_database()
    client = await db._get_client()
    
    # List tables
    res = await client.rpc('exec_sql', {'sql': "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"}).execute()
    print("Tables found:", [r['table_name'] for r in res.data])

if __name__ == "__main__":
    asyncio.run(run())
