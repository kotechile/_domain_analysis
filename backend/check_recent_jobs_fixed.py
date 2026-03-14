import asyncio
from services.database import init_database, get_database
import json

async def check_recent_jobs():
    await init_database()
    db = get_database()
    
    print("Checking recent CSV upload jobs in 'csv_upload_progress':")
    try:
        res = db.client.table('csv_upload_progress').select('*').order('created_at', desc=True).limit(10).execute()
        print(json.dumps(res.data, indent=2))
    except Exception as e:
        print(f"Error checking csv_upload_progress: {e}")

if __name__ == "__main__":
    asyncio.run(check_recent_jobs())
