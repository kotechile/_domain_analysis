import asyncio
import os
import sys
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def inspect_staging():
    await init_database()
    db = get_database()
    
    print("\n--- INSPECTING NAMESILO STAGING DATA ---\n")
    
    try:
        # Fetch a few NameSilo records from staging
        # We look for records that have 2099 expiration to see their source data
        res = db.client.table('auctions_staging')\
            .select('*')\
            .eq('auction_site', 'namesilo')\
            .limit(3)\
            .execute()
            
        if not res.data:
            print("No NameSilo records found in auctions_staging.")
            return

        print(f"Found {len(res.data)} sample records. Inspecting first one:\n")
        
        record = res.data[0]
        print(f"Domain: {record.get('domain')}")
        print(f"Expiration Date: {record.get('expiration_date')}")
        print(f"Job ID: {record.get('job_id')}")
        
        source_data = record.get('source_data')
        if isinstance(source_data, str):
            try:
                source_data = json.loads(source_data)
            except:
                pass
                
        print("\nSource Data Content:")
        print(json.dumps(source_data, indent=2))
        
        # Check specific keys
        if isinstance(source_data, dict):
            print(f"\n'Auction End' present? {'Auction End' in source_data}")
            if 'Auction End' in source_data:
                print(f"Value: '{source_data['Auction End']}'")
            
            # Check for keys that might look like dates
            date_keys = [k for k in source_data.keys() if 'date' in k.lower() or 'end' in k.lower() or 'time' in k.lower()]
            print(f"Potential date keys found: {date_keys}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(inspect_staging())
