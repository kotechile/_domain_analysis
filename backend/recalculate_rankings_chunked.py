#!/usr/bin/env python3
"""
Chunked ranking recalculation script
This processes rankings in smaller batches to avoid PostgreSQL timeouts
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

from services.database import DatabaseService
import structlog

logger = structlog.get_logger()


async def recalculate_rankings_chunked():
    """Recalculate rankings in chunks using direct SQL"""
    db_service = DatabaseService()
    
    if not db_service.client:
        print("Error: Database client not available")
        return
    
    # Get stats
    result = db_service.client.table('auctions').select('id', count='exact').not_.is_('score', 'null').execute()
    scored_count = result.count if hasattr(result, 'count') else 0
    
    print(f"\n=== Recalculating Rankings ===")
    print(f"Scored records: {scored_count:,}")
    print(f"\nThis will process rankings in chunks to avoid timeouts...")
    
    if scored_count == 0:
        print("No scored records to rank.")
        return
    
    # Step 1: Clear existing rankings (optional, but ensures clean state)
    print("\nStep 1: Clearing existing rankings...")
    try:
        clear_result = db_service.client.table('auctions').update({'ranking': None}).not_.is_('score', 'null').execute()
        print("✓ Cleared existing rankings")
    except Exception as e:
        print(f"⚠ Warning: Could not clear rankings: {e}")
        print("Continuing anyway...")
    
    # Step 2: Calculate and update rankings in chunks
    print("\nStep 2: Calculating rankings in chunks...")
    
    chunk_size = 10000
    offset = 0
    total_ranked = 0
    
    while True:
        # Get a chunk of scored records ordered by score DESC
        chunk_result = (
            db_service.client.table('auctions')
            .select('id, score')
            .not_.is_('score', 'null')
            .order('score', desc=True)
            .range(offset, offset + chunk_size - 1)
            .execute()
        )
        
        if not chunk_result.data or len(chunk_result.data) == 0:
            break
        
        # Calculate rankings for this chunk
        records = chunk_result.data
        ranked_records = []
        
        for idx, record in enumerate(records):
            ranking = offset + idx + 1
            ranked_records.append({
                'id': record['id'],
                'ranking': ranking
            })
        
        # Bulk update rankings for this chunk
        for record in ranked_records:
            try:
                db_service.client.table('auctions').update({
                    'ranking': record['ranking'],
                    'updated_at': 'now()'
                }).eq('id', record['id']).execute()
            except Exception as e:
                logger.warning("Failed to update ranking", id=record['id'], error=str(e))
        
        total_ranked += len(ranked_records)
        offset += chunk_size
        
        print(f"  Processed {total_ranked:,} / {scored_count:,} records...")
        
        # Safety check
        if offset > scored_count + chunk_size:
            break
    
    print(f"\n✓ Rankings calculated: {total_ranked:,} records")
    
    # Step 3: Update preferred flags
    print("\nStep 3: Updating preferred flags...")
    try:
        # Get active config
        config_result = (
            db_service.client.table('scoring_config')
            .select('*')
            .eq('is_active', True)
            .order('created_at', desc=True)
            .limit(1)
            .execute()
        )
        
        if config_result.data:
            config = config_result.data[0]
            score_threshold = config.get('score_threshold')
            rank_threshold = config.get('rank_threshold')
            use_both = config.get('use_both_thresholds', False)
            
            # Update preferred flags in chunks
            preferred_count = 0
            pref_offset = 0
            
            while True:
                # Get chunk of ranked records
                pref_chunk = (
                    db_service.client.table('auctions')
                    .select('id, score, ranking')
                    .not_.is_('score', 'null')
                    .not_.is_('ranking', 'null')
                    .range(pref_offset, pref_offset + chunk_size - 1)
                    .execute()
                )
                
                if not pref_chunk.data:
                    break
                
                # Calculate preferred for each record
                for record in pref_chunk.data:
                    score = record.get('score')
                    ranking = record.get('ranking')
                    
                    # Determine if preferred
                    if score_threshold is None and rank_threshold is None:
                        preferred = True
                    elif use_both:
                        preferred = (
                            (score_threshold is None or score >= score_threshold) and
                            (rank_threshold is None or ranking <= rank_threshold)
                        )
                    else:
                        preferred = (
                            (score_threshold is None or score >= score_threshold) or
                            (rank_threshold is None or ranking <= rank_threshold)
                        )
                    
                    # Update preferred flag
                    try:
                        db_service.client.table('auctions').update({
                            'preferred': preferred,
                            'updated_at': 'now()'
                        }).eq('id', record['id']).execute()
                        
                        if preferred:
                            preferred_count += 1
                    except Exception as e:
                        logger.warning("Failed to update preferred", id=record['id'], error=str(e))
                
                pref_offset += chunk_size
                print(f"  Updated preferred flags: {preferred_count:,} preferred so far...")
                
                if pref_offset > scored_count + chunk_size:
                    break
            
            print(f"\n✓ Preferred flags updated: {preferred_count:,} records marked as preferred")
        else:
            print("⚠ No active scoring config found, skipping preferred flag update")
            
    except Exception as e:
        print(f"⚠ Error updating preferred flags: {e}")
    
    print(f"\n=== Ranking Recalculation Complete ===")
    print(f"Total ranked: {total_ranked:,}")
    print(f"Success!")


if __name__ == '__main__':
    asyncio.run(recalculate_rankings_chunked())














