import asyncio
import os
import sys
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def fix_godaddy_links():
    await init_database()
    db = get_database()
    
    print("\n--- FIXING GODADDY LINKS ---\n")
    
    try:
        # Fetch GoDaddy records where link is null
        # We process in chunks to be safe
        page_size = 1000
        offset = 0
        total_fixed = 0
        
        while True:
            print(f"Fetching batch offset={offset}...")
            # Fetch ALL columns so we can bulk upsert safely
            # Note: Supabase range is inclusive.
            res = db.client.table('auctions')\
                .select('*')\
                .eq('auction_site', 'godaddy')\
                .is_('link', 'null')\
                .range(offset, offset + page_size - 1)\
                .execute()
            
            records = res.data
            if not records:
                break
            
            updates = []
            unfixable_count = 0
            
            for r in records:
                source_data = r.get('source_data') or {}
                link = source_data.get('link')
                
                if link:
                    r['link'] = link
                    updates.append(r)
                else:
                    unfixable_count += 1
            
            if updates:
                print(f"Bulk updating {len(updates)} records...")
                try:
                    db.client.table('auctions').upsert(updates).execute()
                    total_fixed += len(updates)
                    print(f"Fixed {total_fixed} so far.")
                except Exception as e:
                    print(f"Error upserting batch: {e}")
                    # If upsert fails, we shouldn't increment offset for these, 
                    # but we might looping forever. 
                    # Let's assume failures are transient or fatal.
                    # For now, treat as unfixable to move on?
                    # Or just raise?
                    # Let's just print and increment offset to avoid infinite loop.
                    unfixable_count += len(updates) 

            # Calculate new offset
            # We skip the records that we couldn't fix (unfixable_count)
            # The fixed records are removed from the view (link IS NOT NULL).
            # So the "unfixable" records slide down to the start of the view (0..unfixable_count-1).
            # We want to start fetching AFTER them.
            # So we add unfixable_count to the current offset.
            offset += unfixable_count
            
            print(f"Batch done. Unfixable in this batch: {unfixable_count}. New offset: {offset}")

            # Safety break if we returned less than page size, meaning we reached end of data
            # Supabase sometimes returns 999 instead of 1000? Let's just rely on empty list.
            # if len(records) < page_size:
            #     print("Reached end of data.")
            #     break
 
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(fix_godaddy_links())
