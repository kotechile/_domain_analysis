import asyncio
import os
import sys
from datetime import datetime
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def analyze_data():
    await init_database()
    db = get_database()
    
    print("\n--- DATA DISTRIBUTION ANALYSIS ---\n")
    
    # 1. Total Count
    try:
        count_res = db.client.table('auctions').select('*', count='exact').limit(1).execute()
        total_count = count_res.count
        print(f"Total Records: {total_count}")
    except Exception as e:
        print(f"Error counting total: {e}")
        return

    if total_count == 0:
        print("Table is empty.")
        return

    # 2. Expiration Date Range
    try:
        # Get min expiration
        min_res = db.client.table('auctions').select('expiration_date').order('expiration_date', desc=False).limit(1).execute()
        min_date = min_res.data[0]['expiration_date'] if min_res.data else "N/A"
        
        # Get max expiration
        max_res = db.client.table('auctions').select('expiration_date').order('expiration_date', desc=True).limit(1).execute()
        max_date = max_res.data[0]['expiration_date'] if max_res.data else "N/A"
        
        print(f"Expiration Date Range: {min_date} to {max_date}")
        
    except Exception as e:
        print(f"Error fetching date range: {e}")

    # 3. Future vs Past
    try:
        now = datetime.utcnow().isoformat()
        future_res = db.client.table('auctions').select('*', count='exact').gt('expiration_date', now).limit(1).execute()
        past_res = db.client.table('auctions').select('*', count='exact').lte('expiration_date', now).limit(1).execute()
        
        print(f"Future Expirations: {future_res.count}")
        print(f"Past/Expired: {past_res.count}")
    except Exception as e:
        print(f"Error counting future/past: {e}")

    # 4. Processed Status
    try:
        processed_res = db.client.table('auctions').select('*', count='exact').eq('processed', True).limit(1).execute()
        unprocessed_res = db.client.table('auctions').select('*', count='exact').eq('processed', False).limit(1).execute()
        
        print(f"Processed: {processed_res.count}")
        print(f"Unprocessed: {unprocessed_res.count}")
    except Exception as e:
        print(f"Error checking processed status: {e}")

    # 5. Sample Data (GoDaddy)
    try:
        sample_res = db.client.table('auctions').select('domain, expiration_date, auction_site, source_data').eq('auction_site', 'godaddy').limit(3).execute()
        print("\nSample Data (GoDaddy):")
        if sample_res.data:
            for item in sample_res.data:
                # Truncate source_data for readability if needed, but we want to see dates
                print(f"Domain: {item['domain']}")
                print(f"Expiration: {item['expiration_date']}")
                print(f"Source Data (keys): {list(item.get('source_data', {}).keys())}")
                print(f"Source Data (dates): {item.get('source_data', {}).get('auctionEndTime')}")
                print("-" * 20)
        else:
            print("No GoDaddy records found.")
    except Exception as e:
        print(f"Error checking sample data: {e}")

if __name__ == "__main__":
    asyncio.run(analyze_data())
