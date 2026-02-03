import asyncio
import os
from datetime import datetime, timezone
from src.services.database import init_database, get_database

async def check_expired_auctions():
    await init_database()
    db = get_database()
    now = datetime.now(timezone.utc).isoformat()
    
    # Expired count (Feb 2nd)
    feb2_start = "2026-02-02T00:00:00Z"
    feb2_end = "2026-02-03T00:00:00Z"
    expired_res = db.client.from_('auctions').select('domain,expiration_date').gte('expiration_date', feb2_start).lt('expiration_date', feb2_end).limit(20).execute()
    
    print(f"Sample of Feb 2nd Expired Auctions:")
    if expired_res.data:
        for row in expired_res.data:
            print(f"- {row['domain']}: {row['expiration_date']}")
    else:
        print("No Feb 2nd expired records found.")
        
    # Check total count of older expired records (using a simpler approach to avoid timeout)
    # We'll just check if there are more than 20
    if len(expired_res.data) == 20:
        print("There are likely many more older expired records.")

if __name__ == "__main__":
    asyncio.run(check_expired_auctions())
