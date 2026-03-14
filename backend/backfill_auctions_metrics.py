import asyncio
import os
import sys
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Helper to get first non-None value from a list of keys
def get_metric(data, keys):
    if not data or not isinstance(data, dict):
        return None
    for k in keys:
        val = data.get(k)
        if val is not None:
            return val
    return None

async def backfill():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        print("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        return

    client = create_client(url, key)
    
    print("Fetching records with has_statistics=True...")
    # Get total count first
    count_response = client.table('auctions').select('count', count='exact').eq('has_statistics', True).execute()
    total = count_response.count if count_response else 0
    print(f"Found {total} records to process.")

    # Process in batches of 100
    batch_size = 100
    processed = 0
    updated_count = 0

    while processed < total:
        print(f"Processing batch {processed} to {min(processed + batch_size, total)}...")
        result = client.table('auctions').select('id, domain, page_statistics').eq('has_statistics', True).range(processed, processed + batch_size - 1).execute()
        
        if not result.data:
            break

        for row in result.data:
            stats = row.get('page_statistics')
            if not stats:
                continue

            update_data = {}
            
            # Map metrics using the same logic as in database.py
            metrics_map = {
                'ranking': ['rank', 'ranking'],
                'backlinks': ['backlinks', 'total_backlinks'],
                'referring_domains': ['referring_domains', 'total_referring_domains'],
                'backlinks_spam_score': ['backlinks_spam_score', 'spam_score'],
                'domain_rating': ['domain_rating', 'dr', 'rank'],
                'organic_traffic': ['organic_traffic', 'etv', 'traffic', 'organic_traffic_est']
            }

            for col, keys in metrics_map.items():
                val = get_metric(stats, keys)
                if val is not None:
                    update_data[col] = val

            if update_data:
                # Update the record
                client.table('auctions').update(update_data).eq('id', row['id']).execute()
                updated_count += 1
            
        processed += len(result.data)
        print(f"Progress: {processed}/{total} (Updated: {updated_count})")

    print(f"\nFinished backfill. Total records updated: {updated_count}")

if __name__ == "__main__":
    asyncio.run(backfill())
EOF
