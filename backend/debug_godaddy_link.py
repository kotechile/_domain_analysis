import asyncio
import os
import sys
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def check_godaddy_links():
    await init_database()
    db = get_database()
    
    print("\n--- CHECKING GODADDY LINKS ---\n")
    
    try:
        # Check count of fixed records
        fixed_res = db.client.table('auctions')\
            .select('*', count='exact')\
            .eq('auction_site', 'godaddy')\
            .not_.is_('link', 'null')\
            .limit(1)\
            .execute()
            
        print(f"GoDaddy records with links: {fixed_res.count}")
        
        # Check count of broken records
        broken_res = db.client.table('auctions')\
            .select('*', count='exact')\
            .eq('auction_site', 'godaddy')\
            .is_('link', 'null')\
            .limit(1)\
            .execute()
            
        print(f"GoDaddy records missing links: {broken_res.count}")
        
    except Exception as e:
        print(f"Error fetching stats: {e}")

if __name__ == "__main__":
    asyncio.run(check_godaddy_links())
