"""
Bulk Analysis Service for processing domain lists and orchestrating bulk analysis workflow
"""

from typing import List, Dict, Any
import structlog
import re

from models.domain_analysis import (
    BulkDomainInput, BulkDomainSyncResult, 
    NamecheapAnalysisResult, NamecheapAnalysisResponse
)
from services.database import get_database
from services.n8n_service import N8NService

logger = structlog.get_logger()


class BulkAnalysisService:
    """Service for bulk domain analysis operations"""
    
    def __init__(self):
        self.db = get_database()
        self.n8n_service = N8NService()
    
    async def sync_domains_to_supabase(self, domains: List[BulkDomainInput]) -> BulkDomainSyncResult:
        """
        Sync domain list to Supabase database
        
        Args:
            domains: List of BulkDomainInput objects
            
        Returns:
            BulkDomainSyncResult with sync statistics
        """
        try:
            result = await self.db.sync_bulk_domains(domains)
            logger.info("Synced domains to Supabase", 
                       created=result.created_count,
                       updated=result.updated_count,
                       skipped=result.skipped_count)
            return result
        except Exception as e:
            logger.error("Failed to sync domains to Supabase", error=str(e))
            raise
    
    async def trigger_bulk_data_collection(self, domains: List[str] = None) -> Dict[str, Any]:
        """
        Trigger n8n webhook for bulk data collection
        
        If domains is None, will automatically get domains missing summary data.
        
        Args:
            domains: Optional list of domain names. If None, fetches missing domains from DB.
            
        Returns:
            Dict with trigger result
        """
        try:
            # Get domains missing summary if not provided
            if domains is None:
                domains = await self.db.get_bulk_domains_missing_summary()
            
            if not domains:
                logger.info("No domains need bulk data collection")
                return {
                    "success": True,
                    "triggered_count": 0,
                    "domains": [],
                    "message": "No domains need data collection"
                }
            
            # Trigger n8n workflow
            trigger_result = await self.n8n_service.trigger_bulk_page_summary_workflow(domains)
            
            if trigger_result:
                logger.info("Triggered bulk data collection", domain_count=len(domains))
                return {
                    "success": True,
                    "triggered_count": len(domains),
                    "domains": domains,
                    "request_id": trigger_result.get("request_id"),
                    "message": f"Triggered data collection for {len(domains)} domains"
                }
            else:
                logger.error("Failed to trigger bulk data collection", domain_count=len(domains))
                return {
                    "success": False,
                    "triggered_count": 0,
                    "domains": domains,
                    "message": "Failed to trigger n8n workflow"
                }
                
        except Exception as e:
            logger.error("Failed to trigger bulk data collection", error=str(e))
            raise
    
    async def analyze_selected_domains(self, domain_names: List[str]) -> NamecheapAnalysisResponse:
        """
        Analyze selected domains by checking for existing DataForSeo data or triggering collection
        
        For each domain:
        - Check bulk_domain_analysis table for existing backlinks_bulk_page_summary
        - If exists: retrieve and return
        - If not exists: create record and trigger n8n webhook
        
        Args:
            domain_names: List of domain names to analyze
            
        Returns:
            NamecheapAnalysisResponse with results for each domain
        """
        try:
            results = []
            has_data_count = 0
            triggered_count = 0
            error_count = 0
            domains_to_trigger = []
            
            for domain_name in domain_names:
                try:
                    # Check if data exists in bulk_domain_analysis table
                    existing = await self.db.get_bulk_domain(domain_name)
                    
                    # Get Namecheap domain data
                    namecheap_domain = await self.db.get_namecheap_domain_by_name(domain_name)
                    
                    if existing and existing.backlinks_bulk_page_summary:
                        # Data exists - return it
                        result = NamecheapAnalysisResult(
                            domain=domain_name,
                            namecheap_data=namecheap_domain,
                            dataforseo_data=existing.backlinks_bulk_page_summary,
                            has_data=True,
                            status="has_data"
                        )
                        results.append(result)
                        has_data_count += 1
                        logger.info("Found existing DataForSeo data", domain=domain_name)
                    else:
                        # Data doesn't exist - need to create record and trigger
                        # First, ensure record exists in bulk_domain_analysis
                        from models.domain_analysis import BulkDomainInput
                        domain_input = BulkDomainInput(domain=domain_name, provider="Namecheap")
                        await self.db.sync_bulk_domains([domain_input])
                        
                        # Add to list for batch triggering
                        domains_to_trigger.append(domain_name)
                        
                        result = NamecheapAnalysisResult(
                            domain=domain_name,
                            namecheap_data=namecheap_domain,
                            has_data=False,
                            status="triggered"
                        )
                        results.append(result)
                        triggered_count += 1
                        logger.info("Triggered DataForSeo collection", domain=domain_name)
                        
                except Exception as e:
                    logger.error("Failed to process domain", domain=domain_name, error=str(e))
                    # Try to get Namecheap data even on error
                    try:
                        namecheap_domain = await self.db.get_namecheap_domain_by_name(domain_name)
                    except:
                        namecheap_domain = None
                    
                    result = NamecheapAnalysisResult(
                        domain=domain_name,
                        namecheap_data=namecheap_domain,
                        has_data=False,
                        status="error",
                        error=str(e)
                    )
                    results.append(result)
                    error_count += 1
            
            # Trigger n8n webhook for all domains that need data collection
            if domains_to_trigger:
                trigger_result = await self.n8n_service.trigger_bulk_page_summary_workflow(domains_to_trigger)
                if not trigger_result:
                    logger.warning("Failed to trigger n8n workflow for some domains", count=len(domains_to_trigger))
            
            return NamecheapAnalysisResponse(
                success=True,
                results=results,
                total_selected=len(domain_names),
                has_data_count=has_data_count,
                triggered_count=triggered_count,
                error_count=error_count
            )
            
        except Exception as e:
            logger.error("Failed to analyze selected domains", error=str(e))
            # Return error response
            error_results = [
                NamecheapAnalysisResult(
                    domain=domain,
                    has_data=False,
                    status="error",
                    error=str(e)
                ) for domain in domain_names
            ]
            return NamecheapAnalysisResponse(
                success=False,
                results=error_results,
                total_selected=len(domain_names),
                error_count=len(domain_names)
            )
