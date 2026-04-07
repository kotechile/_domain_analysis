import asyncio
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "backend/src"))

from services.database import DatabaseService

async def migrate():
    load_dotenv("backend/.env")
    db = DatabaseService()
    client = await db._get_client()
    
    # Add user_id to reports
    try:
        res = await client.rpc('exec_sql', {'sql': 'ALTER TABLE reports ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id)'}).execute()
        print(f"Migration successful: {res.data}")
    except Exception as e:
        print(f"Migration failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(migrate())
