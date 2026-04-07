import asyncio
import os
import json
from datetime import datetime, timezone
from supabase import create_client, Client
from dotenv import load_dotenv

async def check_marketplace_data():
    # Load env from root or backend
    if os.path.exists('backend/.env'):
        load_dotenv('backend/.env')
    elif os.path.exists('.env'):
        load_dotenv('.env')
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("Missing Supabase credentials")
        return

    supabase: Client = create_client(url, key)
    
    now = datetime.now(timezone.utc).isoformat()
    
    print(f"Checking data as of: {now}")
    
    # 1. Total records
    res = supabase.table("auctions").select("count", count="exact").limit(0).execute()
    total = res.count
    print(f"Total domains in auctions: {total}")
    
    # 2. Not deleted
    res = supabase.table("auctions").select("count", count="exact").eq("to_delete", False).limit(0).execute()
    not_deleted = res.count
    print(f"Non-deleted domains: {not_deleted}")
    
    # 3. Not expired
    res = supabase.table("auctions").select("count", count="exact").eq("to_delete", False).gte("expiration_date", now).limit(0).execute()
    not_expired = res.count
    print(f"Non-expired domains (available in UI): {not_expired}")
    
    # 4. Scored (score IS NOT NULL)
    res = supabase.table("auctions").select("count", count="exact").eq("to_delete", False).gte("expiration_date", now).not_.is_("score", "null").limit(0).execute()
    scored = res.count
    print(f"Scored (IS NOT NULL) & Not Expired: {scored}")
    
    # 4b. Score > 0
    res = supabase.table("auctions").select("count", count="exact").eq("to_delete", False).gte("expiration_date", now).gt("score", 0).limit(0).execute()
    scored_gt_0 = res.count
    print(f"Score > 0 & Not Expired: {scored_gt_0}")
    
    # 4c. has_statistics = True
    res = supabase.table("auctions").select("count", count="exact").eq("to_delete", False).gte("expiration_date", now).eq("has_statistics", True).limit(0).execute()
    has_stats = res.count
    print(f"Has Statistics (Flag) & Not Expired: {has_stats}")

    # 5. Has Domain Rating (domain_rating IS NOT NULL)
    res = supabase.table("auctions").select("count", count="exact").eq("to_delete", False).gte("expiration_date", now).not_.is_("domain_rating", "null").limit(0).execute()
    has_dr = res.count
    print(f"Has DR & Not Expired: {has_dr}")

    # 6. Check a few sample records that HAVE a score but NO metrics
    res = supabase.table("auctions").select("domain, score, domain_rating, page_statistics, expiration_date").eq("to_delete", False).gte("expiration_date", now).not_.is_("score", "null").is_("domain_rating", "null").limit(5).execute()
    print("\nSamples (Scored but no DR):")
    for row in res.data:
        print(f" - {row['domain']}: Score={row['score']}, DR={row['domain_rating']}, Exp={row['expiration_date']}")

    # 7. Check a few sample records that HAVE metrics
    res = supabase.table("auctions").select("domain, score, domain_rating, page_statistics").eq("to_delete", False).gte("expiration_date", now).not_.is_("domain_rating", "null").limit(5).execute()
    print("\nSamples (With DR):")
    for row in res.data:
        print(f" - {row['domain']}: Score={row['score']}, DR={row['domain_rating']}, Stats Keys={list(row['page_statistics'].keys()) if row['page_statistics'] else 'None'}")

if __name__ == "__main__":
    asyncio.run(check_marketplace_data())
