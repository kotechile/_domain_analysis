import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def check_mislabeled():
    await init_database()
    db = get_database()
    
    print("\n--- CHECKING FOR MISLABELED NAMESILO RECORDS ---\n")
    
    try:
        # Check for records labeled as 'namecheap' but having 'Auction End' in source_data (which is a NameSilo field)
        print("Scanning 'namecheap' records for NameSilo signatures...")
        
        # We'll limit to a sample if possible, or just count distinct keys
        # But we can query JSONB keys directly in postgres if Supabase allows
        # .not_.is_('source_data->>Auction End', 'null') ? No, syntax is tricky.
        
        # Let's try to fetch a chunk of 'namecheap' records and inspect them python-side.
        # 1000 records should be enough if they are mixed in.
        
        res = db.client.table('auctions').select('domain, auction_site, source_data').eq('auction_site', 'namecheap').limit(1000).execute()
        
        namesilo_count = 0
        namecheap_count = 0
        
        for r in res.data:
            source = r.get('source_data', {})
            if source and 'Auction End' in source:
                namesilo_count += 1
                if namesilo_count <= 5:
                    print(f"  [MISLABELED] Domain: {r['domain']}, Site: {r['auction_site']}, Has 'Auction End'")
            else:
                namecheap_count += 1
                
        print(f"\nResults in sample of {len(res.data)}:")
        print(f"  Verified Namecheap (no 'Auction End'): {namecheap_count}")
        print(f"  Potential NameSilo (has 'Auction End'): {namesilo_count}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_mislabeled())
