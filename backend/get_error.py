import sys
import os
import asyncio

sys.path.append("/Users/jorgefernandezilufi/Documents/_article_research/_domain_analysis/backend/src")

from services.database import get_database, init_database

async def main():
    await init_database()
    db = get_database()
    client = await db._get_client()
    res = await client.table('csv_upload_progress').select('status, error_message, current_stage, total_records, processed_records').eq('filename', 'godaddy_today.json').order('created_at', desc=True).limit(1).execute()
    if res.data:
        print("Status:", res.data[0].get('status'))
        print("Stage:", res.data[0].get('current_stage'))
        print("Total Records:", res.data[0].get('total_records'))
        print("Processed Records:", res.data[0].get('processed_records'))
        print("Error:", res.data[0].get('error_message'))
    else:
        print("Not found")

if __name__ == "__main__":
    asyncio.run(main())
