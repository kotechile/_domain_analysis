import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

async def run_test():
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    supabase = create_client(url, key)
    
    try:
        res = supabase.table('refresh_history').insert({
            'user_id': '942d09c0-58ce-4fe5-b412-f16ac1694a72',
            'batch_size': 1000,
            'credits_spent': 50,
            'filters_used': {}
        }).execute()
        print("Result:", res)
    except Exception as e:
        print("Error Type:", type(e))
        print("Error vars:", vars(e))
        print("Error args:", e.args)

if __name__ == "__main__":
    asyncio.run(run_test())
