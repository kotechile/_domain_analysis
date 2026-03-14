
import asyncio
import sys
import os
from datetime import datetime, timezone

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.database import init_database

async def verify_auctions():
    print("Initializing database connection...")
    try:
        db = await init_database()
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        return

    if not db.client:
        print("Failed to initialize DB client. Check environment variables.")
        return

    print("Querying auctions table...")

    # 1. Total count
    # Note: count='exact' might be slow for large tables, but 1.1M should be okayish or timeout.
    # If it fails, we'll try without count.
    try:
        count_res = db.client.table('auctions').select('*', count='exact', head=True).execute()
        total_count = count_res.count
        print(f"Total auctions count: {total_count}")
    except Exception as e:
        print(f"Failed to get total count: {e}")
        total_count = -1

    # 2. Check expiration dates relative to NOW
    now = datetime.now(timezone.utc).isoformat()
    print(f"Current UTC time for comparison: {now}")

    try:
        # Expired
        expired_res = db.client.table('auctions').select('*', count='exact', head=True).lt('expiration_date', now).execute()
        print(f"Expired auctions ( < {now} ): {expired_res.count}")
    except Exception as e:
        print(f"Failed to get expired count: {e}")

    try:
        # Active
        active_res = db.client.table('auctions').select('*', count='exact', head=True).gte('expiration_date', now).execute()
        print(f"Active auctions ( >= {now} ): {active_res.count}")
        active_count = active_res.count
    except Exception as e:
        print(f"Failed to get active count: {e}")
        active_count = 0

    # 3. Sample active auctions
    if active_count > 0 or active_count is None:
        try:
            print("\nFetching sample of 5 active auctions...")
            sample = db.client.table('auctions').select('domain,expiration_date').gte('expiration_date', now).limit(5).execute()
            for row in sample.data:
                print(f"  {row['domain']}: {row['expiration_date']}")
        except Exception as e:
            print(f"Failed to fetch sample: {e}")

    # 4. Check for NULL expiration
    try:
        null_exp_res = db.client.table('auctions').select('*', count='exact', head=True).is_('expiration_date', 'null').execute()
        print(f"Auctions with NULL expiration: {null_exp_res.count}")
    except Exception as e:
        print(f"Failed to get NULL expiration count: {e}")

    # 5. Check in-range auctions (User scenario)
    user_end_date = "2026-02-19T23:59:59"
    try:
        print(f"\nChecking range: {now} to {user_end_date}...")
        range_res = db.client.table('auctions').select('*', count='exact', head=True)\
            .gte('expiration_date', now)\
            .lte('expiration_date', user_end_date)\
            .execute()
        print(f"Auctions in range: {range_res.count}")
        
        if range_res.count > 0:
            sample = db.client.table('auctions').select('domain,expiration_date')\
                .gte('expiration_date', now)\
                .lte('expiration_date', user_end_date)\
                .limit(5).execute()
            for row in sample.data:
                print(f"  {row['domain']}: {row['expiration_date']}")
    except Exception as e:
        print(f"Failed to check range: {e}")

    # 6. Check min/max expiration date overall
        min_res = db.client.table('auctions').select('expiration_date').order('expiration_date', desc=False).limit(1).execute()
        if min_res.data:
            print(f"  Earliest expiration date: {min_res.data[0]['expiration_date']}")
        
        max_res = db.client.table('auctions').select('expiration_date').order('expiration_date', desc=True).limit(1).execute()
        if max_res.data:
            print(f"  Latest expiration date:   {max_res.data[0]['expiration_date']}")
    except Exception as e:
        print(f"Failed to get min/max dates: {e}")

if __name__ == "__main__":
    asyncio.run(verify_auctions())
