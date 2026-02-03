"""
N8N Service for triggering workflows and handling integration
"""

import httpx
import uuid
from typing import Dict, Any, Optional, List
import structlog
from datetime import datetime

from utils.config import get_settings

logger = structlog.get_logger()


class N8NService:
    """Service for N8N workflow integration"""
    
    def __init__(self):
        self.settings = get_settings()
        self.timeout = self.settings.N8N_TIMEOUT
        self._enabled = self.settings.N8N_ENABLED and bool(self.settings.N8N_WEBHOOK_URL)
        self._summary_enabled = self.settings.N8N_ENABLED and bool(self.settings.N8N_WEBHOOK_URL_SUMMARY) and self.settings.N8N_USE_FOR_SUMMARY
    
    @property
    def enabled(self) -> bool:
        """Check if N8N integration is enabled"""
        return self._enabled
    
    async def trigger_backlinks_workflow(self, domain: str, limit: int = 10000) -> Optional[Dict[str, Any]]:
        """
        Trigger N8N workflow to fetch backlink data
        
        This method triggers the N8N webhook and returns immediately.
        The actual data will be received via the webhook callback endpoint.
        
        Returns:
            Dict with request_id if successful, None if failed
        """
        if not self.enabled:
            logger.warning("N8N integration is disabled", domain=domain)
            return None
        
        try:
            request_id = str(uuid.uuid4())
            callback_url = self.settings.N8N_CALLBACK_URL
            
            if not callback_url:
                logger.error("N8N callback URL not configured")
                return None
            
            # Prepare webhook payload
            payload = {
                "domain": domain,
                "limit": limit,
                "callback_url": callback_url,
                "request_id": request_id,
                "type": "detailed"  # Indicate this is a detailed request
            }
            
            logger.info("Triggering N8N workflow for backlinks", 
                       domain=domain, 
                       request_id=request_id,
                       webhook_url=self.settings.N8N_WEBHOOK_URL)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.settings.N8N_WEBHOOK_URL,
                    json=payload
                )
                
                if response.status_code in [200, 201, 202]:
                    logger.info("N8N workflow triggered successfully", 
                               domain=domain, 
                               request_id=request_id,
                               status_code=response.status_code)
                    return {
                        "request_id": request_id,
                        "domain": domain,
                        "status": "triggered"
                    }
                else:
                    error_text = response.text[:500] if response.text else "No response body"
                    logger.error("N8N workflow trigger failed", 
                               domain=domain,
                               status_code=response.status_code,
                               response=error_text,
                               webhook_url=self.settings.N8N_WEBHOOK_URL)
                    return None
                    
        except httpx.TimeoutException:
            logger.error("N8N workflow trigger timed out", domain=domain, timeout=self.timeout)
            return None
        except Exception as e:
            logger.error("N8N workflow trigger failed", domain=domain, error=str(e))
            return None
    
    async def health_check(self) -> bool:
        """Check if N8N is accessible"""
        if not self.enabled:
            return False
        
        try:
            # Try to ping N8N (if it has a health endpoint)
            # Otherwise, just check if webhook URL is configured
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Try to access N8N base URL (without webhook path)
                base_url = self.settings.N8N_WEBHOOK_URL.rsplit('/', 1)[0] if '/' in self.settings.N8N_WEBHOOK_URL else self.settings.N8N_WEBHOOK_URL
                response = await client.get(f"{base_url}/healthz", follow_redirects=True)
                return response.status_code in [200, 404]  # 404 is OK, means N8N is running
        except Exception as e:
            logger.warning("N8N health check failed", error=str(e))
            # If health check fails, we still consider it available if URL is configured
            return bool(self.settings.N8N_WEBHOOK_URL)
    
    def is_enabled_for_backlinks(self) -> bool:
        """Check if N8N should be used for backlinks"""
        return self.enabled and self.settings.N8N_USE_FOR_BACKLINKS
    
    def is_enabled_for_summary(self) -> bool:
        """Check if N8N should be used for summary backlinks"""
        return self._summary_enabled
    
    async def trigger_backlinks_summary_workflow(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Trigger N8N workflow to fetch backlinks summary data
        
        This method triggers the N8N webhook and returns immediately.
        The actual data will be received via the webhook callback endpoint.
        
        Returns:
            Dict with request_id if successful, None if failed
        """
        if not self.is_enabled_for_summary():
            logger.warning("N8N summary integration is disabled", domain=domain)
            return None
        
        try:
            request_id = str(uuid.uuid4())
            callback_url = self.settings.N8N_CALLBACK_URL
            
            if not callback_url:
                logger.error("N8N callback URL not configured")
                return None
            
            # Use summary-specific callback URL
            if callback_url.endswith("/backlinks"):
                summary_callback_url = callback_url.replace("/backlinks", "/backlinks-summary")
            else:
                summary_callback_url = f"{callback_url}-summary"
            
            # Prepare webhook payload
            payload = {
                "domain": domain,
                "callback_url": summary_callback_url,
                "request_id": request_id,
                "type": "summary"  # Indicate this is a summary request
            }
            
            logger.info("Triggering N8N workflow for backlinks summary", 
                       domain=domain, 
                       request_id=request_id,
                       webhook_url=self.settings.N8N_WEBHOOK_URL_SUMMARY)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.settings.N8N_WEBHOOK_URL_SUMMARY,
                    json=payload
                )
                
                if response.status_code in [200, 201, 202]:
                    logger.info("N8N summary workflow triggered successfully", 
                               domain=domain, 
                               request_id=request_id,
                               status_code=response.status_code)
                    return {
                        "request_id": request_id,
                        "domain": domain,
                        "status": "triggered"
                    }
                else:
                    logger.error("N8N summary workflow trigger failed", 
                               domain=domain,
                               status_code=response.status_code,
                               response=response.text[:200])
                    return None
                    
        except httpx.TimeoutException:
            logger.error("N8N summary workflow trigger timed out", domain=domain, timeout=self.timeout)
            return None
        except Exception as e:
            logger.error("N8N summary workflow trigger failed", domain=domain, error=str(e))
            return None
    
    def _normalize_domain(self, domain: str) -> str:
        """
        Normalize domain name for DataForSEO API
        
        Removes http://, https://, www., trailing slashes, and paths
        Returns clean domain name (e.g., "example.com")
        """
        if not domain:
            return domain
        
        domain = domain.strip().lower()
        
        # Remove protocol
        domain = domain.replace("http://", "").replace("https://", "")
        
        # Remove www.
        if domain.startswith("www."):
            domain = domain[4:]
        
        # Remove trailing slash and any path
        domain = domain.split("/")[0]
        
        # Remove port if present
        domain = domain.split(":")[0]
        
        return domain.strip()
    
    async def trigger_bulk_page_summary_workflow(self, domains: List[str]) -> Optional[Dict[str, Any]]:
        """
        Trigger N8N workflow to fetch bulk page summary data for multiple domains
        
        This method triggers the N8N webhook with a list of domains and returns immediately.
        The actual data will be received via the webhook callback endpoint.
        
        Args:
            domains: List of domain names to analyze (will be normalized)
            
        Returns:
            Dict with request_id if successful, None if failed
        """
        if not self.enabled:
            logger.warning("N8N integration is disabled", domain_count=len(domains))
            return None
        
        if not domains:
            logger.warning("Empty domain list provided")
            return None
        
        try:
            # Normalize all domains to ensure they're in the correct format
            normalized_domains = [self._normalize_domain(d) for d in domains if d]
            
            if not normalized_domains:
                logger.warning("No valid domains after normalization")
                return None
            
            request_id = str(uuid.uuid4())
            callback_url = self.settings.N8N_CALLBACK_URL
            
            if not callback_url:
                logger.error("N8N callback URL not configured")
                return None
            
            # Use bulk-specific callback URL
            if callback_url.endswith("/backlinks") or callback_url.endswith("/backlinks-summary"):
                bulk_callback_url = callback_url.replace("/backlinks", "").replace("/backlinks-summary", "") + "/backlinks-bulk-page-summary"
            else:
                bulk_callback_url = f"{callback_url}/backlinks-bulk-page-summary"
            
            # Prepare webhook payload
            # Send domains as an array - n8n will map this to DataForSEO's "targets" field
            payload = {
                "domains": normalized_domains,  # Array of clean domain strings
                "callback_url": bulk_callback_url,
                "request_id": request_id,
                "type": "bulk_summary"  # Indicate this is a bulk summary request
            }
            
            # Use configured bulk webhook URL
            webhook_url = self.settings.N8N_WEBHOOK_URL_BULK
            
            if not webhook_url:
                logger.error("N8N bulk webhook URL not configured")
                return None
            
            logger.info("Triggering N8N workflow for bulk page summary", 
                       domain_count=len(normalized_domains),
                       original_count=len(domains),
                       request_id=request_id,
                       webhook_url=webhook_url)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    webhook_url,
                    json=payload
                )
                
                if response.status_code in [200, 201, 202]:
                    logger.info("N8N bulk summary workflow triggered successfully", 
                               domain_count=len(normalized_domains),
                               request_id=request_id,
                               status_code=response.status_code)
                    return {
                        "request_id": request_id,
                        "domains": normalized_domains,
                        "domain_count": len(normalized_domains),
                        "status": "triggered"
                    }
                else:
                    error_text = response.text[:500] if response.text else "No response body"
                    logger.error("N8N bulk summary workflow trigger failed", 
                               domain_count=len(domains),
                               status_code=response.status_code,
                               response=error_text,
                               webhook_url=webhook_url)
                    return None
                    
        except httpx.TimeoutException:
            logger.error("N8N bulk summary workflow trigger timed out", domain_count=len(domains), timeout=self.timeout)
            return None
        except Exception as e:
            logger.error("N8N bulk summary workflow trigger failed", domain_count=len(domains), error=str(e))
            return None
    
    async def trigger_bulk_rank_workflow(self, domains: List[str]) -> Optional[Dict[str, Any]]:
        """
        Trigger N8N workflow to fetch bulk rank data for multiple domains (up to 1000)
        
        This method triggers the N8N webhook with a list of domains and returns immediately.
        The actual data will be received via the webhook callback endpoint.
        
        Args:
            domains: List of domain names to analyze (will be normalized, up to 1000)
            
        Returns:
            Dict with request_id if successful, None if failed
        """
        if not self.enabled:
            logger.warning("N8N integration is disabled", domain_count=len(domains))
            return None
        
        if not domains:
            logger.warning("Empty domain list provided")
            return None
        
        try:
            # Normalize all domains to ensure they're in the correct format
            normalized_domains = [self._normalize_domain(d) for d in domains if d]
            
            if not normalized_domains:
                logger.warning("No valid domains after normalization")
                return None
            
            # Limit to 1000 domains (DataForSEO bulk rank endpoint limit)
            if len(normalized_domains) > 1000:
                logger.warning("Domain list exceeds 1000, truncating", 
                             original_count=len(normalized_domains),
                             truncated_count=1000)
                normalized_domains = normalized_domains[:1000]
            
            request_id = str(uuid.uuid4())
            callback_url = self.settings.N8N_CALLBACK_URL
            
            if not callback_url:
                logger.error("N8N callback URL not configured")
                return None
            
            # Use bulk rank-specific callback URL
            if callback_url.endswith("/backlinks") or callback_url.endswith("/backlinks-summary") or callback_url.endswith("/backlinks-bulk-page-summary"):
                bulk_rank_callback_url = callback_url.replace("/backlinks", "").replace("/backlinks-summary", "").replace("/backlinks-bulk-page-summary", "") + "/backlinks-bulk-rank"
            else:
                bulk_rank_callback_url = f"{callback_url}/backlinks-bulk-rank"
            
            # Prepare webhook payload
            payload = {
                "domains": normalized_domains,  # Array of clean domain strings
                "callback_url": bulk_rank_callback_url,
                "request_id": request_id,
                "type": "bulk_rank"  # Indicate this is a bulk rank request
            }
            
            # Use configured bulk rank webhook URL
            webhook_url = self.settings.N8N_WEBHOOK_URL_BULK_RANK
            
            if not webhook_url:
                logger.error("N8N bulk rank webhook URL not configured")
                return None
            
            logger.info("Triggering N8N workflow for bulk rank", 
                       domain_count=len(normalized_domains),
                       original_count=len(domains),
                       request_id=request_id,
                       webhook_url=webhook_url)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    webhook_url,
                    json=payload
                )
                
                if response.status_code in [200, 201, 202]:
                    logger.info("N8N bulk rank workflow triggered successfully", 
                               domain_count=len(normalized_domains),
                               request_id=request_id,
                               status_code=response.status_code)
                    return {
                        "request_id": request_id,
                        "domains": normalized_domains,
                        "domain_count": len(normalized_domains),
                        "status": "triggered"
                    }
                else:
                    error_text = response.text[:500] if response.text else "No response body"
                    logger.error("N8N bulk rank workflow trigger failed", 
                               domain_count=len(domains),
                               status_code=response.status_code,
                               response=error_text,
                               webhook_url=webhook_url)
                    return None
                    
        except httpx.TimeoutException:
            logger.error("N8N bulk rank workflow trigger timed out", domain_count=len(domains), timeout=self.timeout)
            return None
        except Exception as e:
            logger.error("N8N bulk rank workflow trigger failed", domain_count=len(domains), error=str(e))
            return None
    
    async def trigger_bulk_backlinks_workflow(self, domains: List[str]) -> Optional[Dict[str, Any]]:
        """
        Trigger N8N workflow for bulk backlinks analysis (1000 domains max)
        
        This method triggers the N8N webhook for DataForSEO bulk backlink stats.
        The actual data will be received via the webhook callback endpoint.
        
        Args:
            domains: List of domain names (will be normalized and limited to 1000)
            
        Returns:
            Dict with request_id and domain_count if successful, None if failed
        """
        if not self.enabled:
            logger.warning("N8N integration is disabled, cannot trigger bulk backlinks workflow")
            return None
        
        try:
            # Normalize domains (remove www, protocols, paths)
            normalized_domains = []
            for domain in domains:
                if not domain or not isinstance(domain, str):
                    continue
                # Remove protocol if present
                domain = domain.replace("http://", "").replace("https://", "")
                # Remove path if present
                domain = domain.split("/")[0]
                # Remove www. if present
                domain = domain.replace("www.", "").strip().lower()
                if domain and domain not in normalized_domains:
                    normalized_domains.append(domain)
            
            # Limit to 1000 domains (DataForSEO bulk backlinks limit)
            if len(normalized_domains) > 1000:
                logger.warning("Domain list exceeds 1000, truncating", 
                             original_count=len(normalized_domains),
                             truncated_count=1000)
                normalized_domains = normalized_domains[:1000]
            
            request_id = str(uuid.uuid4())
            callback_url = self.settings.N8N_CALLBACK_URL
            
            if not callback_url:
                logger.error("N8N callback URL not configured")
                return None
            
            # Use bulk backlinks-specific callback URL
            if callback_url.endswith("/backlinks") or callback_url.endswith("/backlinks-summary") or callback_url.endswith("/backlinks-bulk-page-summary") or callback_url.endswith("/backlinks-bulk-rank"):
                bulk_backlinks_callback_url = callback_url.replace("/backlinks", "").replace("/backlinks-summary", "").replace("/backlinks-bulk-page-summary", "").replace("/backlinks-bulk-rank", "") + "/backlinks-bulk-backlinks"
            else:
                bulk_backlinks_callback_url = f"{callback_url}/backlinks-bulk-backlinks"
            
            # Prepare webhook payload
            payload = {
                "domains": normalized_domains,  # Array of clean domain strings
                "callback_url": bulk_backlinks_callback_url,
                "request_id": request_id,
                "type": "bulk_backlinks"  # Indicate this is a bulk backlinks request
            }
            
            # Use configured bulk backlinks webhook URL
            webhook_url = self.settings.N8N_WEBHOOK_URL_BULK_BACKLINKS
            
            if not webhook_url:
                logger.error("N8N bulk backlinks webhook URL not configured")
                return None
            
            logger.info("Triggering N8N workflow for bulk backlinks", 
                       domain_count=len(normalized_domains),
                       original_count=len(domains),
                       request_id=request_id,
                       webhook_url=webhook_url)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    webhook_url,
                    json=payload
                )
                
                if response.status_code in [200, 201, 202]:
                    logger.info("N8N bulk backlinks workflow triggered successfully", 
                               domain_count=len(normalized_domains),
                               request_id=request_id,
                               status_code=response.status_code)
                    return {
                        "request_id": request_id,
                        "domains": normalized_domains,
                        "domain_count": len(normalized_domains),
                        "status": "triggered"
                    }
                else:
                    error_text = response.text[:500] if response.text else "No response body"
                    logger.error("N8N bulk backlinks workflow trigger failed", 
                               domain_count=len(domains),
                               status_code=response.status_code,
                               response=error_text,
                               webhook_url=webhook_url)
                    return None
                    
        except httpx.TimeoutException:
            logger.error("N8N bulk backlinks workflow trigger timed out", domain_count=len(domains), timeout=self.timeout)
            return None
        except Exception as e:
            logger.error("N8N bulk backlinks workflow trigger failed", domain_count=len(domains), error=str(e))
            return None
    
    async def trigger_bulk_traffic_batch_workflow(self, domains: List[str]) -> Optional[Dict[str, Any]]:
        """
        Trigger N8N workflow to fetch bulk traffic data for multiple domains
        
        This method triggers the N8N webhook with a list of domains and returns immediately.
        The actual data will be received via the webhook callback endpoint.
        
        Args:
            domains: List of domain names to analyze (will be normalized)
            
        Returns:
            Dict with request_id if successful, None if failed
        """
        if not self.enabled:
            logger.warning("N8N integration is disabled", domain_count=len(domains))
            return None
        
        if not domains:
            logger.warning("Empty domain list provided")
            return None
        
        try:
            # Normalize all domains to ensure they're in the correct format
            normalized_domains = [self._normalize_domain(d) for d in domains if d]
            
            if not normalized_domains:
                logger.warning("No valid domains after normalization")
                return None
            
            request_id = str(uuid.uuid4())
            callback_url = self.settings.N8N_CALLBACK_URL
            
            if not callback_url:
                logger.error("N8N callback URL not configured")
                return None
            
            # Use bulk traffic-specific callback URL
            if callback_url.endswith("/backlinks") or callback_url.endswith("/backlinks-summary"):
                bulk_callback_url = callback_url.replace("/backlinks", "").replace("/backlinks-summary", "") + "/backlinks-bulk-traffic-batch"
            else:
                bulk_callback_url = f"{callback_url}/backlinks-bulk-traffic-batch"
            
            # Prepare webhook payload
            # Send domains as an array - n8n will map this to DataForSEO's "targets" field
            payload = {
                "domains": normalized_domains,  # Array of clean domain strings
                "callback_url": bulk_callback_url,
                "request_id": request_id,
                "type": "bulk_traffic"  # Indicate this is a bulk traffic request
            }
            
            # Use configured bulk traffic webhook URL
            webhook_url = self.settings.N8N_WEBHOOK_URL_BULK_TRAFFIC
            
            if not webhook_url:
                logger.error("N8N bulk traffic webhook URL not configured")
                return None
            
            logger.info("Triggering N8N workflow for bulk traffic batch", 
                       domain_count=len(normalized_domains),
                       original_count=len(domains),
                       request_id=request_id,
                       webhook_url=webhook_url)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    webhook_url,
                    json=payload
                )
                
                if response.status_code in [200, 201, 202]:
                    logger.info("N8N bulk traffic workflow triggered successfully", 
                               domain_count=len(normalized_domains),
                               request_id=request_id,
                               status_code=response.status_code)
                    return {
                        "request_id": request_id,
                        "domains": normalized_domains,
                        "domain_count": len(normalized_domains),
                        "status": "triggered"
                    }
                else:
                    error_text = response.text[:500] if response.text else "No response body"
                    logger.error("N8N bulk traffic workflow trigger failed", 
                               domain_count=len(domains),
                               status_code=response.status_code,
                               response=error_text,
                               webhook_url=webhook_url)
                    return None
                    
        except httpx.TimeoutException:
            logger.error("N8N bulk traffic workflow trigger timed out", domain_count=len(domains), timeout=self.timeout)
            return None
        except Exception as e:
            logger.error("N8N bulk traffic workflow trigger failed", domain_count=len(domains), error=str(e))
            return None
    
    async def trigger_bulk_spam_score_workflow(self, domains: List[str]) -> Optional[Dict[str, Any]]:
        """
        Trigger N8N workflow for bulk spam score analysis (1000 domains max)
        
        This method triggers the N8N webhook for DataForSEO bulk spam scores.
        The actual data will be received via the webhook callback endpoint.
        
        Args:
            domains: List of domain names (will be normalized and limited to 1000)
            
        Returns:
            Dict with request_id and domain_count if successful, None if failed
        """
        if not self.enabled:
            logger.warning("N8N integration is disabled, cannot trigger bulk spam score workflow")
            return None
        
        try:
            # Normalize domains (remove www, protocols, paths)
            normalized_domains = []
            for domain in domains:
                if not domain or not isinstance(domain, str):
                    continue
                # Remove protocol if present
                domain = domain.replace("http://", "").replace("https://", "")
                # Remove path if present
                domain = domain.split("/")[0]
                # Remove www. if present
                domain = domain.replace("www.", "").strip().lower()
                if domain and domain not in normalized_domains:
                    normalized_domains.append(domain)
            
            # Limit to 1000 domains (DataForSEO bulk spam score limit)
            if len(normalized_domains) > 1000:
                logger.warning("Domain list exceeds 1000, truncating", 
                             original_count=len(normalized_domains),
                             truncated_count=1000)
                normalized_domains = normalized_domains[:1000]
            
            request_id = str(uuid.uuid4())
            callback_url = self.settings.N8N_CALLBACK_URL
            
            if not callback_url:
                logger.error("N8N callback URL not configured")
                return None
            
            # Use bulk spam score-specific callback URL
            if callback_url.endswith("/backlinks") or callback_url.endswith("/backlinks-summary") or callback_url.endswith("/backlinks-bulk-page-summary") or callback_url.endswith("/backlinks-bulk-rank") or callback_url.endswith("/backlinks-bulk-backlinks"):
                bulk_spam_score_callback_url = callback_url.replace("/backlinks", "").replace("/backlinks-summary", "").replace("/backlinks-bulk-page-summary", "").replace("/backlinks-bulk-rank", "").replace("/backlinks-bulk-backlinks", "") + "/backlinks-bulk-spam-score"
            else:
                bulk_spam_score_callback_url = f"{callback_url}/backlinks-bulk-spam-score"
            
            # Prepare webhook payload
            payload = {
                "domains": normalized_domains,  # Array of clean domain strings
                "callback_url": bulk_spam_score_callback_url,
                "request_id": request_id,
                "type": "bulk_spam_score"  # Indicate this is a bulk spam score request
            }
            
            # Use configured bulk spam score webhook URL
            webhook_url = self.settings.N8N_WEBHOOK_URL_BULK_SPAM_SCORE
            
            if not webhook_url:
                logger.error("N8N bulk spam score webhook URL not configured")
                return None
            
            logger.info("Triggering N8N workflow for bulk spam score", 
                       domain_count=len(normalized_domains),
                       original_count=len(domains),
                       request_id=request_id,
                       webhook_url=webhook_url)
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    webhook_url,
                    json=payload
                )
                
                if response.status_code in [200, 201, 202]:
                    logger.info("N8N bulk spam score workflow triggered successfully", 
                               domain_count=len(normalized_domains),
                               request_id=request_id,
                               status_code=response.status_code)
                    return {
                        "request_id": request_id,
                        "domains": normalized_domains,
                        "domain_count": len(normalized_domains),
                        "status": "triggered"
                    }
                else:
                    error_text = response.text[:500] if response.text else "No response body"
                    logger.error("N8N bulk spam score workflow trigger failed", 
                               domain_count=len(domains),
                               status_code=response.status_code,
                               response=error_text,
                               webhook_url=webhook_url)
                    return None
                    
        except httpx.TimeoutException:
            logger.error("N8N bulk spam score workflow trigger timed out", domain_count=len(domains), timeout=self.timeout)
            return None
        except Exception as e:
            logger.error("N8N bulk spam score workflow trigger failed", domain_count=len(domains), error=str(e))
            return None
    
    async def trigger_truncate_auctions_workflow(self) -> Optional[Dict[str, Any]]:
        """
        Trigger N8N workflow to truncate the auctions table using SQL
        
        This method triggers an N8N webhook that executes SQL to truncate the table.
        Much faster than REST API deletions for large tables.
        
        Returns:
            Dict with request_id if successful, None if failed
        """
        if not self.enabled:
            logger.warning("N8N integration is disabled, cannot truncate via N8N")
            return None
        
        try:
            request_id = str(uuid.uuid4())
            
            # Use configured truncate webhook URL or construct from base URL
            webhook_url = getattr(self.settings, 'N8N_WEBHOOK_URL_TRUNCATE', None)
            if not webhook_url:
                # Try to construct from base webhook URL
                base_url = self.settings.N8N_WEBHOOK_URL.rsplit('/webhook/', 1)[0] if '/webhook/' in self.settings.N8N_WEBHOOK_URL else None
                if base_url:
                    webhook_url = f"{base_url}/webhook/truncate-auctions"
                else:
                    logger.error("N8N truncate webhook URL not configured")
                    return None
            
            # Prepare webhook payload
            payload = {
                "table": "auctions",
                "action": "truncate",
                "request_id": request_id
            }
            
            logger.info("Triggering N8N workflow to truncate auctions table", 
                       request_id=request_id,
                       webhook_url=webhook_url)
            
            async with httpx.AsyncClient(timeout=120.0) as client:  # Longer timeout for truncate
                response = await client.post(
                    webhook_url,
                    json=payload
                )
                
                if response.status_code in [200, 201, 202]:
                    logger.info("N8N truncate workflow triggered successfully", 
                               request_id=request_id,
                               status_code=response.status_code)
                    return {
                        "request_id": request_id,
                        "status": "triggered",
                        "table": "auctions"
                    }
                else:
                    error_text = response.text[:500] if response.text else "No response body"
                    logger.error("N8N truncate workflow trigger failed", 
                               status_code=response.status_code,
                               response=error_text,
                               webhook_url=webhook_url)
                    return None
                    
        except httpx.TimeoutException:
            logger.error("N8N truncate workflow trigger timed out", timeout=120.0)
            return None
        except Exception as e:
            logger.error("N8N truncate workflow trigger failed", error=str(e))
            return None
    
    async def trigger_auction_scoring_workflow(self, file_path: str, auction_site: str, config_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Trigger N8N workflow to process auction CSV file
        
        This method triggers the N8N auction scoring workflow which will:
        1. Download CSV from Supabase storage
        2. Parse and extract domains, current_bid, dates
        3. Upsert into auctions table
        4. Delete expired records
        5. Execute scoring function
        
        Args:
            file_path: Path to CSV file in Supabase storage (bucket: auction-csvs)
            auction_site: Auction site source ('namecheap', 'godaddy', etc.)
            config_id: Optional config ID for processing
            
        Returns:
            Dict with request_id if successful, None if failed
        """
        if not self.settings.N8N_ENABLED:
            logger.warning("N8N integration is disabled, cannot trigger auction scoring workflow")
            return None
        
        try:
            request_id = str(uuid.uuid4())
            
            # Get webhook URL for auction scoring
            webhook_url = getattr(self.settings, 'N8N_WEBHOOK_URL_AUCTION_SCORING', None)
            if not webhook_url:
                # Try to construct from base URL
                base_url = self.settings.N8N_WEBHOOK_URL.rsplit('/webhook/', 1)[0] if '/webhook/' in self.settings.N8N_WEBHOOK_URL else None
                if base_url:
                    webhook_url = f"{base_url}/webhook/auction-scoring"
                else:
                    logger.error("N8N auction scoring webhook URL not configured")
                    return None
            
            # Include Supabase credentials in payload (N8N blocks env var access)
            payload = {
                "file_path": file_path,
                "auction_site": auction_site,
                "request_id": request_id,
                "supabase_url": self.settings.SUPABASE_URL,
                "supabase_service_role_key": self.settings.SUPABASE_SERVICE_ROLE_KEY or self.settings.SUPABASE_KEY
            }
            
            if config_id:
                payload["config_id"] = config_id
            
            logger.info("Triggering N8N workflow for auction scoring", 
                       request_id=request_id,
                       file_path=file_path,
                       auction_site=auction_site,
                       webhook_url=webhook_url)
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    webhook_url,
                    json=payload
                )
                
                if response.status_code in [200, 201, 202]:
                    logger.info("N8N auction scoring workflow triggered successfully", 
                               request_id=request_id,
                               status_code=response.status_code)
                    return {
                        "request_id": request_id,
                        "status": "triggered",
                        "file_path": file_path,
                        "auction_site": auction_site
                    }
                else:
                    error_text = response.text[:500] if response.text else "No response body"
                    logger.error("N8N auction scoring workflow trigger failed", 
                               status_code=response.status_code,
                               response=error_text,
                               webhook_url=webhook_url)
                    return None
                    
        except httpx.TimeoutException:
            logger.error("N8N auction scoring workflow trigger timed out", timeout=120.0)
            return None
        except Exception as e:
            logger.error("N8N auction scoring workflow trigger failed", error=str(e))
            return None

