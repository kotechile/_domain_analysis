import asyncio
import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.database import init_database

async def test_traffic_update():
    db = await init_database()
    
    domain = 'frlengendsapp.com'
    # Try a large number for traffic
    large_traffic = 3000000000 # 3B, larger than 2^31-1
    
    print(f"Attempting to update {domain} with traffic {large_traffic}...")
    
    try:
        # We'll try to update just organic_traffic first
        update_data = {
            'organic_traffic': large_traffic,
            'updated_at': '2026-03-04T00:00:00Z'
        }
        result = db.client.table('auctions').update(update_data).eq('domain', domain).execute()
        print(f"Update organic_traffic successful: {result.data}")
    except Exception as e:
        print(f"Update organic_traffic failed: {e}")

    print(f"\nAttempting update with keywords_count (which is likely missing)...")
    try:
        update_data = {
            'keywords_count': 100,
            'updated_at': '2026-03-04T00:00:00Z'
        }
        result = db.client.table('auctions').update(update_data).eq('domain', domain).execute()
        print(f"Update keywords_count successful: {result.data}")
    except Exception as e:
        print(f"Update keywords_count failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_traffic_update())
