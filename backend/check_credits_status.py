
import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from services.database import get_database, init_database
from utils.config import get_settings

async def check():
    await init_database()
    db = get_database()
    client = await db._get_client()
    
    print("--- Checking Tables ---")
    tables = ['user_credits', 'credit_transactions', 'action_rates', 'system_settings']
    for table in tables:
        try:
            resp = await client.table(table).select('count', count='exact').limit(0).execute()
            print(f"Table '{table}': {resp.count} records")
        except Exception as e:
            print(f"Table '{table}': FAILED ({str(e)})")

    print("\n--- Checking action_rates ---")
    try:
        resp = await client.table('action_rates').select('*').execute()
        print(f"Action rates: {resp.data}")
    except Exception as e:
        print(f"Failed to get action rates: {str(e)}")

    print("\n--- Checking user_credits sample ---")
    try:
        resp = await client.table('user_credits').select('*').limit(5).execute()
        print(f"Sample data: {resp.data}")
    except Exception as e:
        print(f"Failed to get sample: {str(e)}")

    print("\n--- Checking reports table schema ---")
    try:
        resp = await client.rpc('exec_sql', {'sql': "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'reports'"}).execute()
        print(f"Reports columns: {resp.data}")
    except Exception as e:
        print(f"Failed to get reports columns: {str(e)}")

    print("\n--- Checking active auctions ---")
    try:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        resp = await client.table('auctions').select('count', count='exact').gte('expiration_date', now).execute()
        print(f"Active (non-expired) auctions: {resp.count}")
        
        # Check how many of these have score IS NOT NULL
        resp = await client.table('auctions').select('count', count='exact').gte('expiration_date', now).not_.is_('score', 'null').execute()
        print(f"Active + Scored auctions: {resp.count}")
    except Exception as e:
        print(f"Failed to check active: {str(e)}")

    print("\n--- Checking score distribution ---")
    try:
        resp = await client.table('auctions').select('count', count='exact').eq('score', 0).execute()
        print(f"Score is 0: {resp.count}")
        resp = await client.table('auctions').select('count', count='exact').gt('score', 0).execute()
        print(f"Score > 0: {resp.count}")
        resp = await client.table('auctions').select('count', count='exact').is_('score', 'null').execute()
        print(f"Score is NULL: {resp.count}")
    except Exception as e:
        print(f"Failed to check scores: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check())
