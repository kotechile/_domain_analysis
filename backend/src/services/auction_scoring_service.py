"""
Auction Scoring Service - Hybrid approach using Supabase + Python
Handles complex scoring (LFS, semantic value) for pre-filtered records
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import structlog
import json
import os

from services.database import DatabaseService
from services.domain_scoring_service import DomainScoringService
from models.auctions import Auction
from models.domain_analysis import NamecheapDomain

logger = structlog.get_logger()


class AuctionScoringService:
    """Service for scoring auction records using hybrid Supabase + Python approach"""
    
    def __init__(self):
        self.db_service = DatabaseService()
        self.domain_scoring_service = DomainScoringService()
    
    async def get_unprocessed_batch(
        self, 
        batch_size: int = 10000,
        config_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get a batch of unprocessed auctions with pre-scoring from Supabase
        
        Args:
            batch_size: Number of records to fetch
            config_id: Optional scoring config ID
            
        Returns:
            List of auction records with age_score and filter status
        """
        try:
            if not self.db_service.client:
                raise Exception("Supabase client not available")
            
            # Call the optimized PostgreSQL function
            result = self.db_service.client.rpc(
                'filter_and_pre_score_auctions',
                {
                    'p_batch_limit': batch_size,
                    'p_config_id': config_id
                }
            ).execute()
            
            if result.data:
                logger.info("Fetched unprocessed batch", count=len(result.data), batch_size=batch_size)
                return result.data
            else:
                logger.info("No unprocessed records found")
                return []
                
        except Exception as e:
            logger.error("Failed to fetch unprocessed batch", error=str(e))
            raise
    
    def _convert_to_namecheap_domain(self, auction_data: Dict[str, Any]) -> NamecheapDomain:
        """Convert auction record to NamecheapDomain for scoring"""
        source_data = auction_data.get('source_data', {}) or {}
        
        # Extract registered_date from source_data
        # Handle empty strings and convert to None
        registered_date = None
        if isinstance(source_data, dict):
            reg_date = source_data.get('registered_date') or source_data.get('registeredDate')
            # Convert empty strings, None, or whitespace-only strings to None
            if reg_date:
                if isinstance(reg_date, str):
                    # Strip whitespace and check if it's not empty
                    reg_date_stripped = reg_date.strip()
                    if reg_date_stripped:
                        registered_date = reg_date_stripped
                    else:
                        registered_date = None
                else:
                    # Not a string, use as-is (could be datetime object)
                    registered_date = reg_date
            else:
                registered_date = None
        
        return NamecheapDomain(
            name=auction_data['domain'],
            registered_date=registered_date,
            expiration_date=auction_data.get('expiration_date'),
            # Other fields can be None for scoring purposes
            current_price=None,
            buy_now_price=None,
            bid_count=None,
            watcher_count=None,
            is_premium=None,
            is_partner_sale=None,
            semrush_a_score=None,
            ahrefs_backlinks=None
        )
    
    def calculate_complex_scores(
        self, 
        auction_records: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate LFS and semantic scores for a batch of auctions
        
        Args:
            auction_records: List of auction records from Supabase
            
        Returns:
            Dictionary mapping domain ID to scores: {domain_id: {score, lfs_score, sv_score, age_score}}
        """
        logger.info("Calculating complex scores", record_count=len(auction_records))
        
        scores = {}
        passed_count = 0
        failed_count = 0
        
        for i, auction in enumerate(auction_records):
            try:
                domain_id = auction['id']
                domain_name = auction['domain']
                age_score = float(auction.get('age_score', 0.0))
                passed_filter = auction.get('passed_filter', False)
                filter_reason = auction.get('filter_reason')
                
                # If filter failed, mark as processed with NULL score
                if not passed_filter:
                    scores[domain_id] = {
                        'score': None,
                        'lfs_score': None,
                        'sv_score': None,
                        'age_score': age_score,
                        'filter_reason': filter_reason
                    }
                    failed_count += 1
                    continue
                
                # Convert to NamecheapDomain for scoring
                try:
                    namecheap_domain = self._convert_to_namecheap_domain(auction)
                except Exception as e:
                    logger.warning("Failed to convert auction to NamecheapDomain", 
                                 domain=domain_name, 
                                 domain_id=domain_id,
                                 error=str(e))
                    # Mark as processed with NULL score on conversion error
                    scores[domain_id] = {
                        'score': None,
                        'lfs_score': None,
                        'sv_score': None,
                        'age_score': age_score,
                        'error': f"Conversion error: {str(e)}"
                    }
                    failed_count += 1
                    continue
                
                # Calculate LFS and semantic scores using DomainScoringService
                try:
                    scored = self.domain_scoring_service.score_domain(namecheap_domain)
                except Exception as e:
                    logger.warning("Failed to score domain", 
                                 domain=domain_name, 
                                 domain_id=domain_id,
                                 error=str(e))
                    # Mark as processed with NULL score on scoring error
                    scores[domain_id] = {
                        'score': None,
                        'lfs_score': None,
                        'sv_score': None,
                        'age_score': age_score,
                        'error': f"Scoring error: {str(e)}"
                    }
                    failed_count += 1
                    continue
                
                # Get config weights (default if not available)
                # We'll use the weights from the scoring config, but for now use defaults
                age_weight = 0.40
                lfs_weight = 0.30
                sv_weight = 0.30
                
                # Calculate total score using age_score from DB and complex scores from Python
                lfs_score = scored.lexical_frequency_score or 0.0
                sv_score = scored.semantic_value_score or 0.0
                
                total_score = (
                    (age_score * age_weight) + 
                    (lfs_score * lfs_weight) + 
                    (sv_score * sv_weight)
                )
                
                scores[domain_id] = {
                    'score': round(total_score, 2),
                    'lfs_score': round(lfs_score, 2),
                    'sv_score': round(sv_score, 2),
                    'age_score': age_score
                }
                passed_count += 1
                
                # Log progress every 1000 records
                if (i + 1) % 1000 == 0:
                    logger.info("Scoring progress", processed=i + 1, total=len(auction_records))
                    
            except Exception as e:
                logger.error("Failed to score auction", 
                           domain_id=auction.get('id'), 
                           domain=auction.get('domain'),
                           error=str(e))
                # Mark as processed with NULL score on error
                scores[auction.get('id')] = {
                    'score': None,
                    'lfs_score': None,
                    'sv_score': None,
                    'age_score': auction.get('age_score', 0.0),
                    'error': str(e)
                }
                failed_count += 1
        
        logger.info("Complex scoring complete", 
                   total=len(auction_records),
                   passed=passed_count,
                   failed=failed_count)
        
        return scores
    
    async def update_scores_in_database(
        self, 
        scores: Dict[str, Dict[str, Any]]
    ) -> int:
        """
        Bulk update scores in database using PostgreSQL function
        
        Args:
            scores: Dictionary mapping domain ID to score data
            
        Returns:
            Number of records updated
        """
        try:
            if not self.db_service.client:
                raise Exception("Supabase client not available")
            
            # Format scores for PostgreSQL function
            # Convert UUID keys to strings and prepare JSONB structure
            scores_jsonb = {}
            for domain_id, score_data in scores.items():
                scores_jsonb[domain_id] = {
                    'score': score_data.get('score'),
                    'lfs_score': score_data.get('lfs_score'),
                    'sv_score': score_data.get('sv_score')
                }
            
            # Call bulk update function
            result = self.db_service.client.rpc(
                'bulk_update_auction_scores',
                {'p_scores': scores_jsonb}
            ).execute()
            
            if result.data and 'updated_count' in result.data:
                updated_count = result.data['updated_count']
                logger.info("Updated scores in database", updated_count=updated_count)
                return updated_count
            else:
                logger.warning("No update count returned from bulk_update_auction_scores")
                return 0
                
        except Exception as e:
            logger.error("Failed to update scores in database", error=str(e))
            raise
    
    async def recalculate_rankings(self, use_chunked: bool = True) -> Dict[str, Any]:
        """
        Recalculate global rankings and preferred flags
        
        Args:
            use_chunked: Use chunked approach for large datasets (default: True)
        
        Returns:
            Statistics about ranking recalculation
        """
        try:
            if not self.db_service.client:
                raise Exception("Supabase client not available")
            
            # For large datasets, try chunked approach first
            if use_chunked:
                try:
                    logger.info("Attempting chunked ranking recalculation")
                    result = self.db_service.client.rpc(
                        'recalculate_auction_rankings_chunked',
                        {'p_batch_size': 50000}
                    ).execute()
                    
                    if result.data and result.data.get('success'):
                        logger.info("Chunked ranking recalculation successful", result=result.data)
                        return result.data
                    else:
                        logger.warning("Chunked approach failed, trying standard approach", result=result.data)
                except Exception as chunked_error:
                    error_msg = str(chunked_error)
                    if 'timeout' not in error_msg.lower() and '57014' not in error_msg:
                        logger.warning("Chunked approach error, trying standard", error=error_msg)
                    else:
                        raise  # Re-raise timeout errors
            
            # Fallback to standard approach
            logger.info("Using standard ranking recalculation")
            result = self.db_service.client.rpc('recalculate_auction_rankings').execute()
            
            if result.data:
                logger.info("Recalculated rankings", result=result.data)
                return result.data
            else:
                logger.warning("No result from recalculate_auction_rankings")
                return {'success': False}
                
        except Exception as e:
            logger.error("Failed to recalculate rankings", error=str(e))
            raise
    
    async def process_batch(
        self,
        batch_size: int = 10000,
        config_id: Optional[str] = None,
        recalculate_rankings_after: bool = False  # Changed default to False to avoid timeouts
    ) -> Dict[str, Any]:
        """
        Process a single batch of unprocessed auctions
        
        This is the main orchestration method that:
        1. Fetches unprocessed records with pre-scoring from Supabase
        2. Calculates complex scores (LFS, semantic) in Python
        3. Updates scores back to database
        4. Optionally recalculates global rankings (disabled by default to avoid timeouts)
        
        Args:
            batch_size: Number of records to process
            config_id: Optional scoring config ID
            recalculate_rankings_after: Whether to recalculate rankings after processing
                                      (Default: False - set to True only periodically)
            
        Returns:
            Processing statistics
        """
        logger.info("Starting batch processing", batch_size=batch_size, config_id=config_id)
        
        try:
            # Step 1: Fetch unprocessed batch with pre-scoring
            auction_records = await self.get_unprocessed_batch(batch_size, config_id)
            
            if not auction_records:
                return {
                    'success': True,
                    'processed_count': 0,
                    'message': 'No unprocessed records found'
                }
            
            # Step 2: Calculate complex scores in Python
            scores = self.calculate_complex_scores(auction_records)
            
            # Step 3: Update scores in database
            updated_count = await self.update_scores_in_database(scores)
            
            # Step 4: Recalculate rankings if requested (but skip if large dataset to avoid timeout)
            ranking_stats = {}
            if recalculate_rankings_after:
                try:
                    # Check current scored count to estimate if it might timeout
                    stats = await self.get_processing_stats()
                    scored_count = stats.get('scored_count', 0)
                    
                    if scored_count > 100000:
                        logger.warning("Very large dataset detected, skipping ranking recalculation to avoid timeout", 
                                     scored_count=scored_count)
                        ranking_stats = {
                            'success': False, 
                            'skipped': True,
                            'reason': 'Dataset too large, will recalculate after all processing complete',
                            'scored_count': scored_count
                        }
                    else:
                        ranking_stats = await self.recalculate_rankings()
                except Exception as e:
                    # Log but don't fail the batch if ranking recalculation times out
                    error_msg = str(e)
                    if 'timeout' in error_msg.lower() or '57014' in error_msg:
                        logger.warning("Ranking recalculation timed out (non-critical). Will recalculate after processing completes.", 
                                     error=error_msg)
                    else:
                        logger.warning("Ranking recalculation failed (non-critical)", error=error_msg)
                    ranking_stats = {
                        'success': False, 
                        'error': error_msg, 
                        'note': 'Rankings can be recalculated later using: POST /api/auctions/recalculate-rankings'
                    }
            
            result = {
                'success': True,
                'processed_count': updated_count,
                'total_fetched': len(auction_records),
                'ranking_stats': ranking_stats
            }
            
            logger.info("Batch processing complete", **result)
            return result
            
        except Exception as e:
            logger.error("Batch processing failed", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'processed_count': 0
            }
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get statistics about unprocessed records
        
        Returns:
            Statistics about processing status
        """
        try:
            if not self.db_service.client:
                raise Exception("Supabase client not available")
            
            # Query unprocessed count
            unprocessed_result = (
                self.db_service.client.table('auctions')
                .select('id', count='exact')
                .eq('processed', False)
                .execute()
            )
            
            unprocessed_count = unprocessed_result.count if hasattr(unprocessed_result, 'count') else 0
            
            # Query processed count
            processed_result = (
                self.db_service.client.table('auctions')
                .select('id', count='exact')
                .eq('processed', True)
                .execute()
            )
            
            processed_count = processed_result.count if hasattr(processed_result, 'count') else 0
            
            # Query scored count (processed with non-null score)
            scored_result = (
                self.db_service.client.table('auctions')
                .select('id', count='exact')
                .eq('processed', True)
                .not_.is_('score', 'null')
                .execute()
            )
            
            scored_count = scored_result.count if hasattr(scored_result, 'count') else 0
            
            return {
                'unprocessed_count': unprocessed_count,
                'processed_count': processed_count,
                'scored_count': scored_count,
                'total_count': unprocessed_count + processed_count
            }
            
        except Exception as e:
            logger.error("Failed to get processing stats", error=str(e))
            raise














