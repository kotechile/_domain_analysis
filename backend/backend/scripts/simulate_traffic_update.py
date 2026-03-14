
import asyncio
import os
import sys
from dotenv import load_dotenv
import json

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from services.database import get_database, init_database

async def simulate():
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
    
    await init_database()
    db = get_database()
    
    # Pick a domain to test
    response = db.client.table('auctions').select('domain').limit(1).execute()
    if not response.data:
        print("No auctions found.")
        return
        
    domain = response.data[0]['domain']
    print(f"Testing traffic update for domain: {domain}")
    
    # Mock traffic data from N8N/DataForSEO
    # DataForSEO often returns 'metrics' -> 'organic' -> 'etv' OR top level keys
    mock_traffic_data = {
        "organic_traffic": 1500,
        "metrics": {
            "organic": {
                "etv": 1500,
                "count": 123
            }
        },
        "target": domain
    }
    
    print("Calling update_auction_traffic_data...")
    success = await db.update_auction_traffic_data(domain, mock_traffic_data)
    
    if success:
        print("Update successful. Verifying database content...")
        
        # Fetch back
        check = db.client.table('auctions').select('page_statistics').eq('domain', domain).execute()
        stats = check.data[0]['page_statistics']
        
        print("Page Statistics after update:")
        print(json.dumps(stats, indent=2))
        
        # Verify keys exist
        keys = stats.keys()
        print(f"Keys present: {list(keys)}")
        if 'organic_traffic' in keys:
             print("SUCCESS: organic_traffic key found.")
        else:
             print("FAILURE: organic_traffic key NOT found.")
             
    else:
        print("Update failed (domain not found?)")

if __name__ == "__main__":
    asyncio.run(simulate())
