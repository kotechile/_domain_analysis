import os
import asyncio
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

async def check_stats():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_KEY not found in environment")
        return

    supabase: Client = create_client(url, key)
    
    # 1. Total records
    res_total = supabase.table("auctions").select("count", count="exact").limit(0).execute()
    total = res_total.count
    
    # 2. Scored records (score IS NOT NULL)
    res_scored = supabase.table("auctions").select("count", count="exact").not_.is_("score", "null").limit(0).execute()
    scored = res_scored.count
    
    # 3. Scored > 0
    res_scored_pos = supabase.table("auctions").select("count", count="exact").gt("score", 0).limit(0).execute()
    scored_pos = res_scored_pos.count
    
    # 4. Has statistics
    res_stats = supabase.table("auctions").select("count", count="exact").eq("has_statistics", True).limit(0).execute()
    has_stats = res_stats.count

    # 5. Domain Rating > 0
    res_dr = supabase.table("auctions").select("count", count="exact").gt("domain_rating", 0).limit(0).execute()
    dr_pos = res_dr.count

    print(f"Total Records: {total}")
    print(f"Scored (Not Null): {scored}")
    print(f"Score > 0: {scored_pos}")
    print(f"Has Statistics (true): {has_stats}")
    print(f"Domain Rating > 0: {dr_pos}")

if __name__ == "__main__":
    asyncio.run(check_stats())
