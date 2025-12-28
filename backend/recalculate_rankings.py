#!/usr/bin/env python3
"""
Script to recalculate auction rankings manually
Use this after processing large batches when automatic recalculation times out
"""

import asyncio
import sys
import os
from pathlib import Path

# Change to backend directory so .env file is found
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)

# Add src directory to path
sys.path.insert(0, os.path.join(backend_dir, 'src'))

from services.auction_scoring_service import AuctionScoringService
import structlog

logger = structlog.get_logger()


async def recalculate_rankings():
    """Recalculate rankings for all scored auctions"""
    scoring_service = AuctionScoringService()
    
    # Get stats first
    stats = await scoring_service.get_processing_stats()
    print(f"\n=== Current Statistics ===")
    print(f"Total Records: {stats['total_count']:,}")
    print(f"Processed: {stats['processed_count']:,}")
    print(f"Scored (non-null): {stats['scored_count']:,}")
    print(f"Unprocessed: {stats['unprocessed_count']:,}")
    
    if stats['scored_count'] == 0:
        print("\nNo scored records to rank.")
        return
    
    print(f"\nRecalculating rankings for {stats['scored_count']:,} scored records...")
    print("This may take a few minutes for large datasets...")
    
    try:
        result = await scoring_service.recalculate_rankings()
        
        if result.get('success'):
            ranked_count = result.get('ranked_count', 0)
            print(f"\n✓ Rankings recalculated successfully!")
            print(f"  Ranked records: {ranked_count:,}")
        else:
            print(f"\n✗ Ranking recalculation failed")
            print(f"  Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        error_msg = str(e)
        if 'timeout' in error_msg.lower() or '57014' in error_msg:
            print(f"\n✗ Ranking recalculation timed out")
            print(f"\nThe dataset is too large for the current timeout setting.")
            print(f"\nOptions:")
            print(f"  1. Increase statement_timeout in PostgreSQL:")
            print(f"     SET statement_timeout = '300s';")
            print(f"     SELECT recalculate_auction_rankings();")
            print(f"  2. Or use the optimized chunked approach (see docs)")
        else:
            print(f"\n✗ Ranking recalculation failed: {error_msg}")


if __name__ == '__main__':
    asyncio.run(recalculate_rankings())









