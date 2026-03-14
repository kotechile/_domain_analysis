import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def check_404_domains():
    await init_database()
    db = get_database()
    
    print("\n--- CHECKING DOMAINS RETURNING 404 ---\n")
    
    domains_to_check = [
        "gibe.xyz", "eyyc2026.com", "eyj.ai", "ezpng.com", 
        "ezestatus.com", "eywal.com", "eyitane.com"
    ]
    
    try:
        for domain in domains_to_check:
            print(f"Checking {domain}...")
            
            # 1. Check Auction Record
            auction = db.client.table('auctions').select('*').eq('domain', domain).execute()
            if auction.data:
                print(f"  [OK] Found in Auctions table. Site: {auction.data[0]['auction_site']}, Exp: {auction.data[0]['expiration_date']}")
            else:
                print(f"  [MISSING] Not found in Auctions table.")
            
            # 2. Check Report Record
            report = db.client.table('reports').select('*').eq('domain_name', domain).execute()
            if report.data:
                print(f"  [OK] Found in Reports table. Status: {report.data[0]['status']}")
            else:
                print(f"  [MISSING] Not found in Reports table (Cause of 404 on /reports endpoint?).")
            
            print("-" * 30)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_404_domains())
