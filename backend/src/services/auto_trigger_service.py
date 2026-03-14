"""
Auto-Trigger Service for automatically triggering DataForSEO analysis
"""

from typing import List, Dict, Any
import structlog

from services.database import get_database
from services.bulk_analysis_service import BulkAnalysisService
from models.domain_analysis import ScoredDomain
from utils.config import get_settings

logger = structlog.get_logger()


class AutoTriggerService:
    """Service for auto-triggering DataForSEO analysis based on scoring"""
    
    def __init__(self):
        self.db = get_database()
        self.bulk_service = BulkAnalysisService()
        self.settings = get_settings()
    
    async def check_existing_domains(self, domain_names: List[str]) -> set:
        """
        Check which domains already exist in bulk_domain_analysis table
        
        Args:
            domain_names: List of domain names to check
            
        Returns:
            Set of domain names that exist in the database
        """
        try:
            if not domain_names:
                return set()
            
            # Query database for existing domains (check if they have summary data)
            existing_domains = await self.db.get_bulk_domains_by_names(domain_names)
            existing_set = {d.domain_name for d in existing_domains if d.backlinks_bulk_page_summary is not None}
            
            logger.info("Checked existing domains", 
                       checked=len(domain_names),
                       existing=len(existing_set))
            return existing_set
            
        except Exception as e:
            logger.error("Failed to check existing domains", error=str(e))
            return set()
    
    async def auto_trigger_analysis(
        self,
        ranked_domains: List[ScoredDomain],
        top_3000_domains: List[str],
        top_n: int = None,
        top_rank_threshold: int = None
    ) -> Dict[str, Any]:
        """
        Auto-trigger DataForSEO analysis for top domains that meet criteria
        
        Criteria:
        1. Top N domains from ranked list (sorted by score DESC)
        2. Not in bulk_domain_analysis table
        3. In top 3000 of original CSV
        
        Args:
            ranked_domains: List of ScoredDomain objects (already sorted by score DESC)
            top_3000_domains: List of domain names from top 3000 of CSV
            top_n: Number of top domains to consider (default from config)
            top_rank_threshold: Rank threshold for top domains (default from config)
            
        Returns:
            Dict with trigger results and statistics
        """
        try:
            if top_n is None:
                top_n = self.settings.TOP_DOMAINS_FOR_ANALYSIS
            if top_rank_threshold is None:
                top_rank_threshold = self.settings.TOP_RANK_THRESHOLD
            
            # Get top N domains (only PASS domains)
            top_domains = [s for s in ranked_domains if s.filter_status == 'PASS'][:top_n]
            
            if not top_domains:
                logger.info("No domains to trigger", reason="No passed domains")
                return {
                    "success": True,
                    "triggered_count": 0,
                    "skipped_count": 0,
                    "domains": [],
                    "message": "No domains passed filtering"
                }
            
            # Extract domain names
            top_domain_names = [s.domain.name for s in top_domains]
            
            # Check which domains exist in database
            existing_domains = await self.check_existing_domains(top_domain_names)
            
            # Filter: not in DB AND in top 3000
            top_3000_set = set(top_3000_domains)
            domains_to_trigger = [
                name for name in top_domain_names
                if name not in existing_domains and name in top_3000_set
            ]
            
            if not domains_to_trigger:
                logger.info("No domains to trigger", 
                           reason="All domains either exist in DB or not in top 3000",
                           checked=len(top_domain_names),
                           existing=len(existing_domains),
                           in_top_3000=len([n for n in top_domain_names if n in top_3000_set]))
                return {
                    "success": True,
                    "triggered_count": 0,
                    "skipped_count": len(top_domain_names),
                    "domains": [],
                    "message": "No domains need analysis (all exist in DB or not in top 3000)"
                }
            
            # Trigger DataForSEO bulk pages summary
            logger.info("Triggering DataForSEO analysis", domain_count=len(domains_to_trigger))
            trigger_result = await self.bulk_service.trigger_bulk_data_collection(domains_to_trigger)
            
            if trigger_result.get("success"):
                return {
                    "success": True,
                    "triggered_count": len(domains_to_trigger),
                    "skipped_count": len(top_domain_names) - len(domains_to_trigger),
                    "domains": domains_to_trigger,
                    "request_id": trigger_result.get("request_id"),
                    "message": f"Triggered analysis for {len(domains_to_trigger)} domains"
                }
            else:
                return {
                    "success": False,
                    "triggered_count": 0,
                    "skipped_count": len(top_domain_names),
                    "domains": domains_to_trigger,
                    "message": trigger_result.get("message", "Failed to trigger analysis")
                }
                
        except Exception as e:
            logger.error("Failed to auto-trigger analysis", error=str(e))
            return {
                "success": False,
                "triggered_count": 0,
                "skipped_count": 0,
                "domains": [],
                "message": f"Error: {str(e)}"
            }






















