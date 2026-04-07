
import asyncio
from services.database import get_database, init_database

async def check_rpc():
    await init_database()
    db = get_database()
    
    # Try to get the function definition
    sql = """
    SELECT prosrc 
    FROM pg_proc 
    WHERE proname = 'deduct_credits';
    """
    try:
        # We need to call the client directly 
        client = await db._get_client()
        res = await client.rpc('exec_sql', {'sql': sql}).execute()
        if res.data and len(res.data) > 0:
            print("--- FUNCTION SOURCE ---")
            print(res.data[0]['prosrc'])
            print("--- END ---")
        else:
            print("NOT FOUND!")
        
    except Exception as e:
        print(f"FAILED: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_rpc())
