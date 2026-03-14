import asyncio
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.database import init_database

async def check_column_types():
    db = await init_database()
    
    # Use SQL to get column types
    # self-hosted supabase might not support rpc for list_columns, so we'll try a select on information_schema
    try:
        query = """
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'auctions' 
        AND column_name IN ('organic_traffic', 'keywords_count');
        """
        # We can't run raw SQL easily via client, but we can try to infer from a record
        result = db.client.table('auctions').select('*').limit(1).execute()
        if result.data:
            val = result.data[0].get('organic_traffic')
            print(f"Sample 'organic_traffic' value: {val} (type: {type(val)})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_column_types())
