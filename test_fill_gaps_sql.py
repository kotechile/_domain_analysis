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
    
    # Check constraints
    res = await client.rpc('exec_sql', {'sql': "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = 'reports'::regclass "}).execute()
    print(f"Constraints: {res.data}")

if __name__ == "__main__":
    asyncio.run(check())
