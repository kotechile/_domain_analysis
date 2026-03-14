import asyncio
import os
import sys
from collections import Counter
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def check_date_distribution():
    await init_database()
    db = get_database()
    
    print("\n--- EXPIRATION DATE DISTRIBUTION BY SITE ---\n")
    
    try:
        # We can't do complex GROUP BY queries easily with the Supabase client wrapper 
        # unless we fetch all (too big) or use an RPC (none exists).
        # We will fetch a representative sample for each site.
        
        sites = ['godaddy', 'namecheap', 'namesilo']
        
        for site in sites:
            print(f"\nScanning {site}...")
            
            # Fetch samples (limit 1000)
            query = db.client.table('auctions').select('domain, expiration_date, offer_type').eq('auction_site', site)
            
            if site == 'namecheap':
                 # Specifically look for auctions to see if they exist and have dates
                 # We already saw buy_now has 2099
                 query = query.eq('offer_type', 'auction')
            
            res = query.limit(500).execute()
                
            if not res.data:
                print(f"  No records found for {site}.")
                continue
                
            years = []
            types = []
            
            for item in res.data:
                exp_str = item.get('expiration_date')
                offer_type = item.get('offer_type', 'unknown')
                
                if exp_str:
                    try:
                        dt = datetime.fromisoformat(exp_str.replace('Z', '+00:00'))
                        years.append(dt.year)
                        
                        # Inspect a 2099 case specifically
                        if dt.year == 2099 and len(years) < 5: 
                             print(f"  [2099 Sample] {item.get('domain')} ({offer_type})")
                    except:
                        years.append('invalid')
                else:
                    years.append('none')
                    
                types.append(offer_type)
            
            year_counts = Counter(years)
            type_counts = Counter(types)
            
            print(f"  Year Distribution: {dict(year_counts)}")
            print(f"  Type Distribution: {dict(type_counts)}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_date_distribution())
