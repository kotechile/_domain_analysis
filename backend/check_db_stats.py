import asyncio
import os
from supabase import create_client, Client
from dotenv import load_dotenv

async def check_counts():
    load_dotenv('backend/.env')
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("Missing Supabase credentials")
        return

    # Use verify=False if needed for self-hosted
    supabase: Client = create_client(url, key)
    
    # Check auctions count
    res = supabase.table("auctions").select("count").execute()
    print(f"Auctions Total: {res.data[0]['count'] if res.data else 0}")
    
    # Check auctions_staging count
    res = supabase.table("auctions_staging").select("count").execute()
    print(f"Staging Total: {res.data[0]['count'] if res.data else 0}")
    
    # Check csv_upload_progress
    res = supabase.table("csv_upload_progress").select("*").order("created_at", desc=True).limit(5).execute()
    print("\n--- Recent Jobs ---")
    for row in res.data:
        print(f"File: {row['filename']}, Status: {row['status']}, Stage: {row['current_stage']}, Processed: {row['processed_records']}/{row['total_records']}")

if __name__ == "__main__":
    asyncio.run(check_counts())
