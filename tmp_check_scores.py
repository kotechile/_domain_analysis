
import asyncio
import os
import sys
from typing import Optional

# Add the backend src to path
sys.path.append(os.path.join(os.getcwd(), 'backend', 'src'))

from services.database import DatabaseService

async def check_scores():
    db = DatabaseService()
    client = await db._get_client()
    
    # Check total
    total_res = await client.table('auctions').select('*', count='exact').limit(0).execute()
    total_count = total_res.count if hasattr(total_res, 'count') else 0

    # Check count of NULL scores
    null_res = await client.table('auctions').select('*', count='exact').is_('score', 'null').limit(0).execute()
    null_count = null_res.count if hasattr(null_res, 'count') else 0
    
    # Check count of 0 scores
    zero_res = await client.table('auctions').select('*', count='exact').eq('score', 0).limit(0).execute()
    zero_count = zero_res.count if hasattr(zero_res, 'count') else 0
    
    # Check count of > 0 scores
    pos_res = await client.table('auctions').select('*', count='exact').gt('score', 0).limit(0).execute()
    pos_count = pos_res.count if hasattr(pos_res, 'count') else 0
    
    # Check samples of 0 vs null
    records = await client.table('auctions').select('domain, score').limit(5).execute()

    print(f"Total auctions: {total_count}")
    print(f"NULL scores: {null_count}")
    print(f"Zero (0) scores: {zero_count}")
    print(f"Positive (>0) scores: {pos_count}")
    print(f"Samples: {records.data}")

if __name__ == "__main__":
    asyncio.run(check_scores())
