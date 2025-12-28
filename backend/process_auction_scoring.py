#!/usr/bin/env python3
"""
CLI script to process auction scoring in batches

Usage:
    python process_auction_scoring.py --batch-size 10000 --batches 10
    python process_auction_scoring.py --batch-size 5000 --continuous
    python process_auction_scoring.py --stats-only
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path
from typing import Optional

# Change to backend directory so .env file is found
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)

# Add src directory to path so imports work correctly (matches pattern from other backend scripts)
sys.path.insert(0, os.path.join(backend_dir, 'src'))

from services.auction_scoring_service import AuctionScoringService
from utils.config import get_settings
import structlog

logger = structlog.get_logger()


async def process_scoring(
    batch_size: int = 10000,
    num_batches: Optional[int] = None,
    continuous: bool = False,
    config_id: Optional[str] = None,
    recalculate_rankings: bool = False,  # Changed default to False - recalculate only periodically
    recalculate_every_n_batches: int = 10  # Recalculate rankings every N batches (default: every 10 batches)
):
    """
    Process auction scoring in batches
    
    Args:
        batch_size: Number of records per batch
        num_batches: Number of batches to process (None = process all)
        continuous: Keep processing until no more unprocessed records
        config_id: Optional scoring config ID
        recalculate_rankings: Whether to recalculate rankings after each batch
    """
    scoring_service = AuctionScoringService()
    
    # Get initial stats
    stats = await scoring_service.get_processing_stats()
    logger.info("Starting scoring process", **stats)
    
    if stats['unprocessed_count'] == 0:
        logger.info("No unprocessed records found")
        return
    
    batch_num = 0
    total_processed = 0
    
    try:
        while True:
            # Check if we should continue
            if num_batches is not None and batch_num >= num_batches:
                logger.info("Reached batch limit", batch_num=batch_num, limit=num_batches)
                break
            
            # Get current stats
            stats = await scoring_service.get_processing_stats()
            if stats['unprocessed_count'] == 0:
                logger.info("All records processed", total_processed=total_processed)
                break
            
            batch_num += 1
            logger.info("Processing batch", batch_num=batch_num, batch_size=batch_size)
            
            # Determine if we should recalculate rankings for this batch
            # Recalculate if explicitly requested OR every N batches
            # But skip if we have too many scored records (to avoid timeouts)
            should_recalculate = False
            if recalculate_rankings:
                # User explicitly requested, but warn if dataset is large
                stats = await scoring_service.get_processing_stats()
                if stats.get('scored_count', 0) > 50000:
                    logger.warning("Large dataset detected, ranking recalculation may timeout. Consider running it separately after processing.")
                should_recalculate = True
            elif batch_num % recalculate_every_n_batches == 0:
                # Check if we have too many records - if so, skip to avoid timeout
                stats = await scoring_service.get_processing_stats()
                if stats.get('scored_count', 0) < 50000:
                    should_recalculate = True
                else:
                    logger.info("Skipping ranking recalculation (large dataset, will recalculate at end)", 
                              scored_count=stats.get('scored_count', 0))
            
            # Process batch
            result = await scoring_service.process_batch(
                batch_size=batch_size,
                config_id=config_id,
                recalculate_rankings_after=should_recalculate
            )
            
            if result['success']:
                processed = result.get('processed_count', 0)
                total_processed += processed
                logger.info("Batch complete", 
                          batch_num=batch_num,
                          processed=processed,
                          total_processed=total_processed)
            else:
                logger.error("Batch failed", batch_num=batch_num, error=result.get('error'))
                break
            
            # If not continuous, stop after one batch
            if not continuous and num_batches is None:
                break
            
            # Small delay between batches to avoid overwhelming the system
            if continuous or (num_batches and batch_num < num_batches):
                await asyncio.sleep(1)
        
        # Final stats
        final_stats = await scoring_service.get_processing_stats()
        logger.info("Scoring process complete", 
                   batches_processed=batch_num,
                   total_processed=total_processed,
                   **final_stats)
        
        # Recalculate rankings one final time if we processed any batches
        if batch_num > 0:
            scored_count = final_stats.get('scored_count', 0)
            if scored_count > 0:
                logger.info("Recalculating final rankings...", scored_count=scored_count)
                try:
                    ranking_result = await scoring_service.recalculate_rankings()
                    if ranking_result.get('success'):
                        logger.info("Final rankings recalculated successfully", 
                                  ranked_count=ranking_result.get('ranked_count', 0))
                    else:
                        logger.warning("Final ranking recalculation returned unsuccessful result", result=ranking_result)
                except Exception as e:
                    error_msg = str(e)
                    if 'timeout' in error_msg.lower() or '57014' in error_msg:
                        logger.warning("Final ranking recalculation timed out. Dataset may be too large.", error=error_msg)
                        logger.info("To recalculate rankings manually, you can:")
                        logger.info("  1. Use API: POST /api/auctions/recalculate-rankings")
                        logger.info("  2. Or increase statement_timeout in PostgreSQL and try again")
                    else:
                        logger.warning("Final ranking recalculation failed", error=error_msg)
                        logger.info("You can manually recalculate rankings later using: POST /api/auctions/recalculate-rankings")
            else:
                logger.info("No scored records to rank")
        
    except KeyboardInterrupt:
        logger.info("Scoring interrupted by user", batches_processed=batch_num, total_processed=total_processed)
    except Exception as e:
        logger.error("Scoring process failed", error=str(e), batches_processed=batch_num)
        raise


async def show_stats():
    """Show current scoring statistics"""
    scoring_service = AuctionScoringService()
    stats = await scoring_service.get_processing_stats()
    
    print("\n=== Auction Scoring Statistics ===")
    print(f"Total Records: {stats['total_count']:,}")
    print(f"Processed: {stats['processed_count']:,}")
    print(f"Unprocessed: {stats['unprocessed_count']:,}")
    print(f"Scored (non-null): {stats['scored_count']:,}")
    
    if stats['total_count'] > 0:
        processed_pct = (stats['processed_count'] / stats['total_count']) * 100
        print(f"\nProgress: {processed_pct:.1f}%")
    
    if stats['unprocessed_count'] > 0:
        batches_needed = (stats['unprocessed_count'] + 9999) // 10000
        print(f"Estimated batches needed (10K per batch): {batches_needed}")
    
    print()


def main():
    parser = argparse.ArgumentParser(description='Process auction scoring in batches')
    parser.add_argument('--batch-size', type=int, default=10000, 
                       help='Number of records per batch (default: 10000)')
    parser.add_argument('--batches', type=int, default=None,
                       help='Number of batches to process (default: process all)')
    parser.add_argument('--continuous', action='store_true',
                       help='Keep processing until no more unprocessed records')
    parser.add_argument('--config-id', type=str, default=None,
                       help='Optional scoring config ID')
    parser.add_argument('--recalculate-rankings', action='store_true',
                       help='Recalculate rankings after each batch (default: False, recalculates every 10 batches)')
    parser.add_argument('--recalculate-every', type=int, default=10,
                       help='Recalculate rankings every N batches (default: 10)')
    parser.add_argument('--stats-only', action='store_true',
                       help='Only show statistics, do not process')
    
    args = parser.parse_args()
    
    if args.stats_only:
        asyncio.run(show_stats())
    else:
        asyncio.run(process_scoring(
            batch_size=args.batch_size,
            num_batches=args.batches,
            continuous=args.continuous,
            config_id=args.config_id,
            recalculate_rankings=args.recalculate_rankings,
            recalculate_every_n_batches=args.recalculate_every
        ))


if __name__ == '__main__':
    main()









