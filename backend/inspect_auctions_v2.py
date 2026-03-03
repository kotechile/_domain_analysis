import asyncio
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

async def inspect():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        print("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        return

    client = create_client(url, key)
    
    # Find records with statistics
    result = client.table('auctions').select('domain, page_statistics, organic_traffic, domain_rating').eq('has_statistics', True).limit(5).execute()
    
    if not result.data:
        print("No records found with has_statistics=True")
        return
        
    for row in result.data:
        print(f"Domain: {row['domain']}")
        print(f"Organic Traffic column: {row['organic_traffic']}")
        print(f"Domain Rating column: {row['domain_rating']}")
        # Mask potentially sensitive data but show keys
        stats = row['page_statistics']
        if stats:
             print(f"Page Statistics Keys: {list(stats.keys())}")
             # Print a few relevant values
             print(f"  traffic: {stats.get('traffic')}")
             print(f"  organic_traffic: {stats.get('organic_traffic')}")
             print(f"  etv: {stats.get('etv')}")
             print(f"  metrics->organic->etv: {stats.get('metrics', {}).get('organic', {}).get('etv') if isinstance(stats.get('metrics'), dict) else 'N/A'}")
        else:
             print("  Page Statistics is Empty/Null")
        print("-" * 20)

if __name__ == "__main__":
    asyncio.run(inspect())
