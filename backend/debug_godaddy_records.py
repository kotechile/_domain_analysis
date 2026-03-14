import asyncio
from services.database import init_database, get_database
from datetime import datetime

async def debug_godaddy():
    await init_database()
    db = get_database()
    
    # 1. Check auction_site values
    print("Checking unique auction_site values:")
    res = db.client.table('auctions').select('auction_site').execute()
    sites = set(r['auction_site'] for r in res.data if r.get('auction_site'))
    print(f"Unique auction sites in DB: {sites}")

    # 2. Check GoDaddy records specifically
    print("\nChecking GoDaddy records:")
    # Try different variations of GoDaddy
    for site_query in ['godaddy', 'go daddy', 'GoDaddy']:
        res = db.client.table('auctions').select('domain, auction_site, expiration_date').eq('auction_site', site_query).limit(5).execute()
        print(f"Sample for '{site_query}': {len(res.data)} records found.")
        for r in res.data:
            print(f"  {r['domain']} | {r['auction_site']} | {r['expiration_date']}")

    # 3. Check for any records with 'godaddy' in them
    res = db.client.table('auctions').select('count', count='exact').ilike('auction_site', '%godaddy%').execute()
    print(f"\nTotal records with 'godaddy' (ilike): {res.count}")

    # 4. Check expiration dates for GoDaddy
    now = datetime.utcnow().isoformat()
    res = db.client.table('auctions').select('count', count='exact').ilike('auction_site', '%godaddy%').gt('expiration_date', now).execute()
    print(f"Total GoDaddy records with future expiration: {res.count}")

    # 5. Inspect source_data for one GoDaddy record
    print("\nInspecting source_data for one GoDaddy record:")
    res = db.client.table('auctions').select('domain, expiration_date, source_data, offer_type').eq('auction_site', 'godaddy').limit(1).execute()
    if res.data:
        r = res.data[0]
        print(f"Domain: {r['domain']}")
        print(f"Expiration Date (DB): {r['expiration_date']}")
        print(f"Offer Type: {r.get('offer_type')}")
        print(f"Source Data auctionEndTime: {r.get('source_data', {}).get('auctionEndTime')}")
        # print(f"Full Source Data: {r['source_data']}")
    else:
        print("No GoDaddy records found to inspect.")

    # 6. Check counts by site and status
    print("\nAuction counts by site and status (Active = expiration > now):")
    res = db.client.table('auctions').select('auction_site, expiration_date, offer_type').execute()
    
    sites = {}
    for r in res.data:
        site = r['auction_site']
        if site not in sites:
            sites[site] = {'active': 0, 'expired': 0, 'buy_now': 0}
        
        if r.get('offer_type') == 'buy_now':
            sites[site]['buy_now'] += 1
            sites[site]['active'] += 1 # Buy now are always considered active
        else:
            exp_date = r.get('expiration_date')
            if exp_date:
                # Simple string comparison for ISO dates works for naive UTC comparison here
                if exp_date > now:
                    sites[site]['active'] += 1
                else:
                    sites[site]['expired'] += 1
    
    import json
    print(json.dumps(sites, indent=2))

if __name__ == "__main__":
    asyncio.run(debug_godaddy())
