import os
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

def check_dates():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_KEY not found in environment")
        return

    supabase: Client = create_client(url, key)
    
    # Get min/max expiration dates
    res = supabase.table("auctions").select("expiration_date").order("expiration_date", desc=False).limit(1).execute()
    min_date = res.data[0]['expiration_date'] if res.data else "None"
    
    res = supabase.table("auctions").select("expiration_date").order("expiration_date", desc=True).limit(1).execute()
    max_date = res.data[0]['expiration_date'] if res.data else "None"
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Count future auctions
    res_future = supabase.table("auctions").select("count", count="exact").gte("expiration_date", now).limit(0).execute()
    future_count = res_future.count

    print(f"Now: {now}")
    print(f"Min Expiration Date: {min_date}")
    print(f"Max Expiration Date: {max_date}")
    print(f"Future Auctions count: {future_count}")

if __name__ == "__main__":
    check_dates()
