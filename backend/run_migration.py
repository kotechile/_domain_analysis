import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

async def run_migration():
    print("Initializing DB...")
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    supabase = create_client(url, key)
    
    with open("credits_v2_migration.sql", "r") as f:
        sql = f.read()
    
    print("Running migration...")
    try:
        res = supabase.rpc('exec_sql', {'sql': sql}).execute()
        print("Result:", res)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(run_migration())
