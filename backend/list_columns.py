
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
    
    # List columns of user_profiles
    res = await client.rpc('exec_sql', {'sql': "SELECT column_name FROM information_schema.columns WHERE table_name = 'user_profiles'"}).execute()
    print("Columns in user_profiles:", [r['column_name'] for r in res.data])

if __name__ == "__main__":
    asyncio.run(run())
