"""
External API services for domain analysis
"""

import httpx
import asyncio
from typing import Dict, Any, Optional, List
from uuid import UUID
import structlog
from datetime import datetime, timedelta

from utils.config import get_settings
from models.domain_analysis import DataForSEOMetrics, DataSource, OrganicMetrics, PaidMetrics
from services.database import get_database
from services.secrets_service import get_secrets_service
from services.usage_tracking import UsageTrackingService

logger = structlog.get_logger()


class DataForSEOService:
    """Service for DataForSEO API integration"""
    
    def __init__(self):
        self.settings = get_settings()
        self.secrets_service = get_secrets_service()
        self.usage_tracking = UsageTrackingService()
        self.timeout = 30.0
        self._credentials = None
    
    async def _get_credentials(self) -> Optional[Dict[str, str]]:
        """Get DataForSEO credentials from secrets service"""
        if self._credentials is None:
            self._credentials = await self.secrets_service.get_dataforseo_credentials()
            
            # Fix API URL if it points to marketing site instead of API
            if self._credentials and 'api_url' in self._credentials:
                api_url = self._credentials['api_url']
                if 'dataforseo.com' in api_url and 'api.dataforseo.com' not in api_url:
                    logger.warning("Correcting DataForSEO API URL", original=api_url, new="https://api.dataforseo.com/v3")
                    self._credentials['api_url'] = "https://api.dataforseo.com/v3"
                    
        return self._credentials
    
    async def health_check(self) -> bool:
        """Check if DataForSEO API is accessible"""
        try:
            credentials = await self._get_credentials()
            if not credentials:
                logger.warning("DataForSEO credentials not available")
                return False
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Use a simple endpoint that should return a valid response
                # DataForSEO doesn't have a /ping endpoint, so we'll test with a basic call
                response = await client.get(
                    f"{credentials['api_url']}/ping",
                    auth=(credentials['login'], credentials['password'])
                )
                # DataForSEO returns 404 for /ping but with proper API response structure
                # This indicates the API is accessible and credentials are valid
                if response.status_code == 404 and 'version' in response.text:
                    logger.info("DataForSEO API accessible (ping endpoint returns 404 as expected)")
                    return True
                elif response.status_code == 200:
                    return True
                else:
                    logger.warning("DataForSEO API returned unexpected response", 
                                 status_code=response.status_code, response=response.text[:200])
                    return False
        except Exception as e:
            logger.warning("DataForSEO health check failed", error=str(e))
            return False
    
    async def get_domain_analytics(self, domain: str, user_id: Optional[UUID] = None) -> Optional[Dict[str, Any]]:
        """Get domain analytics data from DataForSEO"""
        try:
            # Get credentials
            credentials = await self._get_credentials()
            if not credentials:
                logger.error("DataForSEO credentials not available")
                return None
            
            # Check cache first
            db = get_database()
            cached_data = await db.get_raw_data(domain, DataSource.DATAFORSEO)
            if cached_data:
                logger.info("Using cached DataForSEO data", domain=domain)
                return cached_data
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Check if N8N is enabled for summary - if so, skip direct backlinks summary call
                from services.n8n_service import N8NService
                n8n_service = N8NService()
                use_n8n_summary = n8n_service.is_enabled_for_summary()
                
                backlinks_summary_data = None
                if not use_n8n_summary:
                    # Get backlinks summary data using v3 API (as per documentation)
                    # Only if N8N is not enabled for summary
                    post_data = {}
                    post_data[len(post_data)] = {
                        "target": domain,
                        "internal_list_limit": 10,
                        "include_subdomains": True,
                        "backlinks_filters": ["dofollow", "=", True],
                        "backlinks_status_type": "all"
                    }
                    
                    url = f"{credentials['api_url']}/backlinks/summary/live"
                    logger.info("Making DataForSEO backlinks summary request", url=url, domain=domain)
                    backlinks_summary_response = await client.post(
                        url,
                        auth=(credentials['login'], credentials['password']),
                        json=post_data
                    )
                    
                    # Handle backlinks summary response
                    if backlinks_summary_response.status_code == 200:
                        response_data = backlinks_summary_response.json()
                        if response_data.get("status_code") == 20000 and response_data.get("tasks"):
                            backlinks_summary_data = response_data["tasks"][0].get("result", [])
                            if backlinks_summary_data:
                                backlinks_summary_data = backlinks_summary_data[0]
                    else:
                        logger.warning("DataForSEO backlinks summary request failed", 
                                     domain=domain, status=backlinks_summary_response.status_code)
                else:
                    logger.info("Skipping direct backlinks summary call - using N8N instead", domain=domain)
                    # Try to get summary from cache (it should be there if N8N already called back)
                    if cached_data and cached_data.get("backlinks_summary"):
                        backlinks_summary_data = cached_data["backlinks_summary"]
                        logger.info("Using cached N8N backlinks summary data", domain=domain)
                
                # Get domain rank overview using v3 API (as per documentation)
                domain_rank_post_data = {}
                domain_rank_post_data[len(domain_rank_post_data)] = {
                    "target": domain,
                    "language_name": "English",
                    "location_code": 2840
                }
                
                domain_rank_url = f"{credentials['api_url']}/dataforseo_labs/google/domain_rank_overview/live"
                logger.info("Making DataForSEO domain rank overview request", url=domain_rank_url, domain=domain)
                domain_rank_response = await client.post(
                    domain_rank_url,
                    auth=(credentials['login'], credentials['password']),
                    json=domain_rank_post_data
                )
                
                # Handle domain rank response
                domain_rank_data = None
                if domain_rank_response.status_code == 200:
                    response_data = domain_rank_response.json()
                    if response_data.get("status_code") == 20000 and response_data.get("tasks"):
                        result = response_data["tasks"][0].get("result", [])
                        if result and result[0].get("items"):
                            domain_rank_data = result[0]["items"][0].get("metrics", {})
                else:
                    logger.warning("DataForSEO domain rank overview request failed", 
                                 domain=domain, status=domain_rank_response.status_code)
                
                # Skip detailed backlinks and keywords collection to save costs
                # These will be loaded on-demand when users request them via the frontend
                backlinks_data = None
                keywords_data = None
                
                logger.info("Skipping detailed backlinks and keywords collection to save costs", domain=domain)
                
                # Combine all data
                combined_data = {
                    "domain_rank": domain_rank_data or {},
                    "backlinks_summary": backlinks_summary_data or {},
                    "backlinks": backlinks_data or {},
                    "keywords": keywords_data or {},
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Cache the data
                await db.save_raw_data(domain, DataSource.DATAFORSEO, combined_data)
                
                # Track usage
                await self.usage_tracking.track_usage(
                    user_id=user_id,
                    resource_type='dataforseo',
                    operation='domain_analytics',
                    provider='dataforseo',
                    model='v3',
                    cost_estimated=0.0, # Add cost logic later if needed
                    details={'domain': domain}
                )

                logger.info("DataForSEO data retrieved successfully", domain=domain)
                return combined_data
                
        except Exception as e:
            logger.error("Failed to get DataForSEO data", domain=domain, error=str(e))
            return None
    
    async def get_historical_rank_overview(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get historical rank overview from DataForSEO"""
        try:
            credentials = await self._get_credentials()
            if not credentials:
                logger.error("DataForSEO credentials not available")
                return None
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{credentials['api_url']}/dataforseo_labs/google/historical_rank_overview/live"
                
                # Calculate dates (last 4 years)
                end_date = datetime.utcnow() - timedelta(days=1)
                start_date = end_date - timedelta(days=365*4)
                
                post_data = [{
                    "target": domain,
                    "language_name": "English",
                    "location_code": 2840,
                    "date_from": start_date.strftime("%Y-%m-%d"),
                    "date_to": end_date.strftime("%Y-%m-%d")
                }]
                
                logger.info("Making DataForSEO historical rank overview request", url=url, domain=domain)
                response = await client.post(
                    url,
                    auth=(credentials['login'], credentials['password']),
                    json=post_data
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status_code") == 20000 and data.get("tasks"):
                        result = data["tasks"][0].get("result", [])
                        if result and result[0].get("items"):
                            logger.info("DataForSEO historical rank overview retrieved successfully", domain=domain)
                            return result[0]
                
                logger.warning("DataForSEO historical rank overview request failed", 
                             domain=domain, status=response.status_code)
                return None
                
        except Exception as e:
            logger.error("Failed to get DataForSEO historical rank overview", domain=domain, error=str(e))
            return None

    async def get_traffic_analytics_history(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get traffic analytics history from DataForSEO"""
        try:
            credentials = await self._get_credentials()
            if not credentials:
                logger.error("DataForSEO credentials not available")
                return None
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{credentials['api_url']}/traffic_analytics/history/live"
                
                # Calculate dates (last 2 years approx for traffic analytics often differs in availability but usage is similar)
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=365*2)
                
                post_data = [{
                    "target": domain,
                    "language_name": "English",
                    "location_code": 2840,
                    "date_from": start_date.strftime("%Y-%m-%d"),
                    "date_to": end_date.strftime("%Y-%m-%d")
                }]
                
                logger.info("Making DataForSEO traffic analytics history request", url=url, domain=domain)
                response = await client.post(
                    url,
                    auth=(credentials['login'], credentials['password']),
                    json=post_data
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status_code") == 20000 and data.get("tasks"):
                        result = data["tasks"][0].get("result", [])
                        if result and result[0].get("items"):
                            logger.info("DataForSEO traffic analytics history retrieved successfully", domain=domain)
                            return result[0]
                
                logger.warning("DataForSEO traffic analytics history request failed", 
                             domain=domain, status=response.status_code)
                return None
                
        except Exception as e:
            logger.error("Failed to get DataForSEO traffic analytics history", domain=domain, error=str(e))
            return None

    def parse_domain_metrics(self, data: Dict[str, Any]) -> DataForSEOMetrics:
        """Parse DataForSEO data into domain metrics"""
        try:
            domain_rank = data.get("domain_rank", {})
            backlinks_summary = data.get("backlinks_summary", {})
            backlinks = data.get("backlinks", {})
            keywords = data.get("keywords", {})
            
            # Debug logging
            logger.info("Parsing DataForSEO metrics", 
                       domain_rank_keys=list(domain_rank.keys()),
                       backlinks_summary_keys=list(backlinks_summary.keys()),
                       backlinks_keys=list(backlinks.keys()),
                       keywords_keys=list(keywords.keys()))
            
            # Debug the actual values we're trying to extract
            total_backlinks = backlinks_summary.get("backlinks", 0)
            total_referring_domains = backlinks_summary.get("referring_domains", 0)
            organic_metrics = domain_rank.get("organic", {})
            organic_traffic_est = organic_metrics.get("etv", 0)
            total_keywords = organic_metrics.get("count", 0)
            
            logger.info("Extracted values", 
                       total_backlinks=total_backlinks,
                       total_referring_domains=total_referring_domains,
                       organic_traffic_est=organic_traffic_est,
                       total_keywords=total_keywords)
            
            # Extract referring domains info from detailed backlinks
            referring_domains_info = []
            if backlinks.get("items"):
                for item in backlinks["items"][:100]:  # Top 100
                    referring_domains_info.append({
                        "domain": item.get("domain", ""),
                        "domain_rank": item.get("domain_rank", 0),
                        "anchor_text": item.get("anchor", ""),
                        "backlinks_count": item.get("backlinks_count", 0),
                        "first_seen": item.get("first_seen", ""),
                        "last_seen": item.get("last_seen", "")
                    })
            
            # Extract keywords info from new structure
            organic_keywords = []
            if keywords.get("items"):
                for item in keywords["items"][:1000]:  # Top 1000
                    keyword_data = item.get("keyword_data", {})
                    keyword_info = keyword_data.get("keyword_info", {})
                    ranked_element = item.get("ranked_serp_element", {})
                    serp_item = ranked_element.get("serp_item", {})
                    
                    organic_keywords.append({
                        "keyword": keyword_data.get("keyword", ""),
                        "rank": serp_item.get("rank_absolute", 0),
                        "search_volume": keyword_info.get("search_volume", 0),
                        "cpc": keyword_info.get("cpc", 0.0),
                        "competition": keyword_info.get("competition_level", ""),
                        "etv": serp_item.get("etv", 0.0),
                        "url": serp_item.get("url", ""),
                        "title": serp_item.get("title", ""),
                        "description": serp_item.get("description", ""),
                        "keyword_difficulty": keyword_data.get("keyword_properties", {}).get("keyword_difficulty", 0)
                    })
            
            # Use backlinks summary data for main metrics if available
            total_backlinks = backlinks_summary.get("backlinks", 0)
            total_referring_domains = backlinks_summary.get("referring_domains", 0)
            
            # Extract organic metrics from domain rank overview (if available)
            organic_metrics = domain_rank.get("organic", {})
            organic_traffic_est = organic_metrics.get("etv", 0)  # Estimated Traffic Value
            total_keywords = organic_metrics.get("count", 0)  # Total keywords count
            
            # Use DataForSEO's rank from backlinks summary (PageRank-like metric)
            dataforseo_rank = backlinks_summary.get("rank", 0)
            
            # Fallback to calculated DR if DataForSEO rank is not available
            if dataforseo_rank == 0:
                logger.warning("DataForSEO rank not available, falling back to calculated DR")
                calculated_dr = self._calculate_domain_rating(
                    total_backlinks=total_backlinks,
                    total_referring_domains=total_referring_domains,
                    organic_traffic_est=organic_traffic_est,
                    total_keywords=total_keywords,
                    referring_domains_info=referring_domains_info
                )
            else:
                # Convert DataForSEO rank (0-1000 scale) to 0-100 scale to match DR
                calculated_dr = dataforseo_rank / 10.0
                logger.info("Using DataForSEO rank", rank=dataforseo_rank, converted_dr=calculated_dr)
            
            # Create organic and paid metrics objects safely
            organic_metrics_obj = None
            if organic_metrics:
                try:
                    organic_metrics_obj = OrganicMetrics(**organic_metrics)
                except Exception as e:
                    logger.warning("Failed to create OrganicMetrics", error=str(e), organic_metrics=organic_metrics)
            
            paid_metrics_obj = None
            if domain_rank.get("paid"):
                try:
                    paid_metrics_obj = PaidMetrics(**domain_rank.get("paid", {}))
                except Exception as e:
                    logger.warning("Failed to create PaidMetrics", error=str(e), paid_metrics=domain_rank.get("paid"))
            
            logger.info("Successfully parsed DataForSEO metrics", 
                       total_backlinks=total_backlinks,
                       total_referring_domains=total_referring_domains,
                       organic_traffic_est=organic_traffic_est,
                       total_keywords=total_keywords,
                       calculated_dr=calculated_dr)
            
            return DataForSEOMetrics(
                domain_rating_dr=calculated_dr,
                organic_traffic_est=organic_traffic_est,
                total_referring_domains=total_referring_domains,
                total_backlinks=total_backlinks,
                referring_domains_info=referring_domains_info,
                organic_keywords=organic_keywords,
                total_keywords=total_keywords,
                organic_metrics=organic_metrics_obj,
                paid_metrics=paid_metrics_obj
            )
            
        except Exception as e:
            logger.error("Failed to parse DataForSEO metrics", error=str(e), 
                        data_keys=list(data.keys()) if data else "No data")
            return DataForSEOMetrics()
    
    def _calculate_domain_rating(self, total_backlinks: int, total_referring_domains: int, 
                                organic_traffic_est: float, total_keywords: int, 
                                referring_domains_info: List[Dict[str, Any]]) -> float:
        """
        Calculate Domain Rating (DR) based on available metrics.
        Uses a logarithmic scale similar to Ahrefs DR (0-100).
        Detects sandbox environment and adjusts calculation accordingly.
        """
        try:
            # Detect if we're in a sandbox environment
            # Sandbox typically has very high numbers that don't make sense for real domains
            is_sandbox = (
                total_backlinks > 1000000 or  # Over 1M backlinks is unrealistic for most domains
                total_referring_domains > 10000 or  # Over 10K referring domains is very high
                organic_traffic_est > 50000  # Over $50K ETV is very high
            )
            
            if is_sandbox:
                logger.warning("Sandbox environment detected - using simplified DR calculation")
                # Simplified calculation for sandbox - more conservative scoring
                backlinks_score = min(30, 5 * (1 + (total_backlinks / 10000) ** 0.3)) if total_backlinks > 0 else 0
                referring_domains_score = min(20, 3 * (1 + (total_referring_domains / 1000) ** 0.3)) if total_referring_domains > 0 else 0
                traffic_score = min(10, 2 * (1 + (organic_traffic_est / 50000) ** 0.2)) if organic_traffic_est > 0 else 0
                keywords_score = min(5, 1 * (1 + (total_keywords / 5000) ** 0.2)) if total_keywords > 0 else 0
                quality_bonus = 0
            else:
                # Production calculation
                backlinks_score = min(50, 10 * (1 + (total_backlinks / 1000) ** 0.5)) if total_backlinks > 0 else 0
                referring_domains_score = min(30, 5 * (1 + (total_referring_domains / 100) ** 0.5)) if total_referring_domains > 0 else 0
                traffic_score = min(15, 3 * (1 + (organic_traffic_est / 10000) ** 0.3)) if organic_traffic_est > 0 else 0
                keywords_score = min(10, 2 * (1 + (total_keywords / 1000) ** 0.3)) if total_keywords > 0 else 0
                
                # Quality bonus from referring domains (if we have detailed data)
                quality_bonus = 0
                if referring_domains_info:
                    high_authority_domains = sum(1 for domain in referring_domains_info 
                                               if domain.get('domain_rank', 0) >= 70)
                    quality_bonus = min(15, high_authority_domains * 2)
            
            # Calculate final DR (0-100 scale)
            calculated_dr = min(100, backlinks_score + referring_domains_score + 
                               traffic_score + keywords_score + quality_bonus)
            
            # Ensure minimum score for domains with any backlinks
            if total_backlinks > 0 and calculated_dr < 1:
                calculated_dr = 1
            
            logger.info("Calculated Domain Rating", 
                       dr=calculated_dr,
                       is_sandbox=is_sandbox,
                       backlinks=total_backlinks,
                       referring_domains=total_referring_domains,
                       traffic_est=organic_traffic_est,
                       keywords=total_keywords)
            
            return round(calculated_dr, 1)
            
        except Exception as e:
            logger.error("Failed to calculate Domain Rating", error=str(e))
            return 0.0
    
    async def get_backlinks_summary(self, domain: str, user_id: Optional[UUID] = None) -> Optional[Dict[str, Any]]:
        """Get backlinks summary data from DataForSEO v3 API"""
        try:
            # Get credentials
            credentials = await self._get_credentials()
            if not credentials:
                logger.error("DataForSEO credentials not available")
                return None
            
            # Check cache first
            db = get_database()
            cached_data = await db.get_raw_data(domain, DataSource.DATAFORSEO)
            if cached_data and cached_data.get("backlinks_summary"):
                logger.info("Using cached DataForSEO backlinks summary data", domain=domain)
                return cached_data["backlinks_summary"]
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Get backlinks summary data using proper format
                post_data = {}
                post_data[len(post_data)] = {
                    "target": domain,
                    "internal_list_limit": 10,
                    "include_subdomains": True,
                    "backlinks_filters": ["dofollow", "=", True],
                    "backlinks_status_type": "all"
                }
                
                response = await client.post(
                    f"{credentials['api_url']}/backlinks/summary/live",
                    auth=(credentials['login'], credentials['password']),
                    json=post_data
                )
                
                if response.status_code != 200:
                    logger.error("DataForSEO backlinks summary request failed", 
                               domain=domain, status=response.status_code)
                    return None
                
                data = response.json()
                
                # Extract the result from the response
                if data.get("status_code") == 20000 and data.get("tasks"):
                    result = data["tasks"][0].get("result", [])
                    if result:
                        summary_data = result[0]
                        logger.info("DataForSEO backlinks summary retrieved successfully", domain=domain)
                        return summary_data
                
                logger.warning("No backlinks summary data found", domain=domain)
                return None
                
        except Exception as e:
            logger.error("Failed to get DataForSEO backlinks summary", domain=domain, error=str(e))
            return None

    async def get_detailed_backlinks(self, domain: str, limit: int = 100, user_id: Optional[UUID] = None) -> Optional[Dict[str, Any]]:
        """Get detailed backlinks data from DataForSEO v3 API (on-demand)"""
        try:
            credentials = await self._get_credentials()
            if not credentials:
                logger.error("DataForSEO credentials not available")
                return None
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Get detailed backlinks data
                post_data = {}
                post_data[len(post_data)] = {
                    "target": domain,
                    "limit": limit,
                    "mode": "as_is",
                    "filters": ["dofollow", "=", True]
                }
                
                response = await client.post(
                    f"{credentials['api_url']}/backlinks/backlinks/live",
                    auth=(credentials['login'], credentials['password']),
                    json=post_data
                )
                
                if response.status_code != 200:
                    logger.error("DataForSEO detailed backlinks request failed", 
                               domain=domain, status=response.status_code)
                    return None
                
                data = response.json()
                
                # Extract the result from the response
                if data.get("status_code") == 20000 and data.get("tasks"):
                    result = data["tasks"][0].get("result", [])
                    if result:
                        backlinks_data = result[0]
                        logger.info("DataForSEO detailed backlinks retrieved successfully", 
                                  domain=domain, count=backlinks_data.get("total_count", 0))
                        
                        await self.usage_tracking.track_usage(
                            user_id=user_id,
                            resource_type='dataforseo',
                            operation='detailed_backlinks',
                            provider='dataforseo',
                            model='v3',
                            details={'domain': domain, 'limit': limit}
                        )
                        return backlinks_data
                
                logger.warning("No detailed backlinks data found", domain=domain)
                return None
                
        except Exception as e:
            logger.error("Failed to get DataForSEO detailed backlinks", domain=domain, error=str(e))
            return None

    async def get_detailed_keywords(self, domain: str, limit: int = 1000, user_id: Optional[UUID] = None) -> Optional[Dict[str, Any]]:
        """Get detailed keywords data from DataForSEO v3 API (on-demand)"""
        try:
            credentials = await self._get_credentials()
            if not credentials:
                logger.error("DataForSEO credentials not available")
                return None
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Get detailed keywords data
                post_data = {}
                post_data[len(post_data)] = {
                    "target": domain,
                    "language_name": "English",
                    "location_name": "United States",
                    "load_rank_absolute": True,
                    "limit": limit
                }
                
                response = await client.post(
                    f"{credentials['api_url']}/dataforseo_labs/google/ranked_keywords/live",
                    auth=(credentials['login'], credentials['password']),
                    json=post_data
                )
                
                if response.status_code != 200:
                    logger.error("DataForSEO detailed keywords request failed", 
                               domain=domain, status=response.status_code)
                    return None
                
                data = response.json()
                
                # Extract the result from the response
                if data.get("status_code") == 20000 and data.get("tasks"):
                    result = data["tasks"][0].get("result", [])
                    if result:
                        keywords_data = result[0]
                        logger.info("DataForSEO detailed keywords retrieved successfully", 
                                  domain=domain, count=len(keywords_data.get("items", [])))
                                  
                        await self.usage_tracking.track_usage(
                            user_id=user_id,
                            resource_type='dataforseo',
                            operation='detailed_keywords',
                            provider='dataforseo',
                            model='v3',
                            details={'domain': domain, 'limit': limit}
                        )
                        return keywords_data
                
                logger.warning("No detailed keywords data found", domain=domain)
                return None
                
        except Exception as e:
            logger.error("Failed to get DataForSEO detailed keywords", domain=domain, error=str(e))
            return None

    async def get_referring_domains(self, domain: str, limit: int = 800, user_id: Optional[UUID] = None) -> Optional[Dict[str, Any]]:
        """Get referring domains data from DataForSEO v3 API (on-demand)"""
        try:
            credentials = await self._get_credentials()
            if not credentials:
                logger.error("DataForSEO credentials not available")
                return None
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Get referring domains data using the backlinks endpoint with aggregation
                post_data = {}
                post_data[len(post_data)] = {
                    "target": domain,
                    "limit": limit,
                    "mode": "as_is",
                    "filters": ["dofollow", "=", True],
                    "order_by": ["domain_from_rank,desc"]
                }
                
                response = await client.post(
                    f"{credentials['api_url']}/backlinks/backlinks/live",
                    auth=(credentials['login'], credentials['password']),
                    json=post_data
                )
                
                if response.status_code != 200:
                    logger.error("DataForSEO referring domains request failed", 
                               domain=domain, status=response.status_code)
                    return None
                
                data = response.json()
                
                # Extract the result from the response
                if data.get("status_code") == 20000 and data.get("tasks"):
                    result = data["tasks"][0].get("result", [])
                    if result:
                        backlinks_data = result[0]
                        
                        # Group by domain to get unique referring domains
                        referring_domains = {}
                        for item in backlinks_data.get("items", []):
                            domain_from = item.get("domain_from", "")
                            if domain_from not in referring_domains:
                                referring_domains[domain_from] = {
                                    "domain": domain_from,
                                    "domain_rank": item.get("domain_from_rank", 0),
                                    "backlinks_count": 0,
                                    "first_seen": item.get("first_seen", ""),
                                    "last_seen": item.get("last_seen", "")
                                }
                            referring_domains[domain_from]["backlinks_count"] += 1
                        
                        # Convert to list and sort by domain rank
                        referring_domains_list = list(referring_domains.values())
                        referring_domains_list.sort(key=lambda x: x.get("domain_rank", 0), reverse=True)
                        
                        referring_domains_data = {
                            "total_count": len(referring_domains_list),
                            "items": referring_domains_list[:limit]
                        }
                        
                        logger.info("DataForSEO referring domains retrieved successfully", 
                                  domain=domain, count=len(referring_domains_data.get("items", [])))
                                  
                        await self.usage_tracking.track_usage(
                            user_id=user_id,
                            resource_type='dataforseo',
                            operation='referring_domains',
                            provider='dataforseo',
                            model='v3',
                            details={'domain': domain, 'limit': limit}
                        )
                        return referring_domains_data
                
                logger.warning("No referring domains data found", domain=domain)
                return None
                
        except Exception as e:
            logger.error("Failed to get DataForSEO referring domains", domain=domain, error=str(e))
            return None


class WaybackMachineService:
    """Service for Wayback Machine API integration"""
    
    def __init__(self):
        self.base_url = "http://web.archive.org/cdx/search/cdx"
        self.timeout = 30.0
    
    async def health_check(self) -> bool:
        """Check if Wayback Machine API is accessible"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.base_url,
                    params={"url": "example.com", "limit": 1}
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning("Wayback Machine health check failed", error=str(e))
            return False
    
    async def get_domain_history(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get domain history from Wayback Machine"""
        try:
            # Check cache first
            db = get_database()
            cached_data = await db.get_raw_data(domain, DataSource.WAYBACK_MACHINE)
            if cached_data:
                logger.info("Using cached Wayback Machine data", domain=domain)
                return cached_data
            
            # Format domain for Wayback Machine API (remove protocol for domain match)
            wayback_url = domain.replace("https://", "").replace("http://", "").replace("www.", "")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.base_url,
                    params={
                        "url": wayback_url,
                        "output": "json",
                        "limit": 1000,
                        "collapse": "timestamp:8",  # Group by day
                        "matchType": "domain"
                    }
                )
                
                if response.status_code != 200:
                    logger.error("Wayback Machine request failed", 
                               domain=domain, 
                               wayback_url=wayback_url,
                               status=response.status_code,
                               response_text=response.text[:200] if response.text else None)
                    return None
                
                try:
                    data = response.json()
                except Exception as json_error:
                    logger.error("Failed to parse Wayback Machine JSON response", 
                               domain=domain,
                               response_text=response.text[:500] if response.text else None,
                               error=str(json_error))
                    return None
                
                if not data or len(data) < 2:  # Header + data
                    logger.warning("No Wayback Machine data found", 
                                 domain=domain,
                                 response_length=len(data) if data else 0,
                                 response_preview=str(data)[:200] if data else None)
                    return {
                        "total_captures": 0,
                        "first_capture_year": None,
                        "last_capture_date": None,
                        "captures": [],
                        "timestamp": datetime.utcnow().isoformat()
                    }
                
                # Parse data (skip header row)
                captures = []
                for row in data[1:]:
                    if len(row) >= 3:
                        captures.append({
                            "timestamp": row[1],
                            "url": row[2],
                            "status": row[3] if len(row) > 3 else "200"
                        })
                
                # Calculate summary statistics
                total_captures = len(captures)
                first_capture_year = None
                last_capture_date = None
                
                if captures:
                    first_capture = min(captures, key=lambda x: x["timestamp"])
                    last_capture = max(captures, key=lambda x: x["timestamp"])
                    
                    first_capture_year = int(first_capture["timestamp"][:4])
                    last_capture_date = datetime.strptime(
                        last_capture["timestamp"], "%Y%m%d%H%M%S"
                    ).isoformat()
                
                result = {
                    "total_captures": total_captures,
                    "first_capture_year": first_capture_year,
                    "last_capture_date": last_capture_date,
                    "captures": captures[:100],  # Limit to first 100 for storage
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Cache the data
                await db.save_raw_data(domain, DataSource.WAYBACK_MACHINE, result)
                
                logger.info("Wayback Machine data retrieved successfully", 
                          domain=domain, captures=total_captures)
                return result
                
        except httpx.TimeoutException:
            logger.error("Wayback Machine request timed out", domain=domain, timeout=self.timeout)
            return None
        except httpx.RequestError as e:
            logger.error("Wayback Machine request error", domain=domain, error=str(e), error_type=type(e).__name__)
            return None
        except Exception as e:
            logger.error("Failed to get Wayback Machine data", 
                        domain=domain, 
                        error=str(e), 
                        error_type=type(e).__name__,
                        exc_info=True)
            return None


class LLMService:
    """Service for LLM integration (Gemini and OpenAI)"""
    
    def __init__(self):
        self.settings = get_settings()
        self.settings = get_settings()
        self.secrets_service = get_secrets_service()
        self.usage_tracking = UsageTrackingService()
        self.timeout = 60.0
        self._gemini_key = None
        self._openai_key = None
        self._provider = None
    
    async def _get_provider_and_key(self) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Get available LLM provider, API key, and model name"""
        config = await self.secrets_service.get_active_llm_config()
        
        if config:
            raw_provider = config.get('provider', '').lower()
            api_key = config.get('api_key')
            model_name = config.get('model_name')
            
            # Normalize provider names
            if raw_provider == 'google' or raw_provider == 'gemini':
                self._provider = 'gemini'
                self._gemini_key = api_key
            elif 'openai' in raw_provider:
                self._provider = 'openai'
                self._openai_key = api_key
            else:
                self._provider = raw_provider
                
            return self._provider, api_key, model_name
            
        # Fallback to legacy behavior if DB config returns nothing (unlikely with new setup but safe)
        if self._provider is None:
            # Try Gemini first
            gemini_key = await self.secrets_service.get_gemini_credentials()
            if gemini_key:
                self._provider = "gemini"
                self._gemini_key = gemini_key
                return self._provider, self._gemini_key, "gemini-2.0-flash-exp"
            
            # Try OpenAI as fallback
            openai_key = await self.secrets_service.get_openai_credentials()
            if openai_key:
                self._provider = "openai"
                self._openai_key = openai_key
                return self._provider, self._openai_key, "gpt-4o-mini"
            
            logger.error("No LLM provider credentials available")
            return None, None, None
        
        if self._provider == "gemini":
            return self._provider, self._gemini_key, "gemini-2.0-flash-exp"
        else:
            return self._provider, self._openai_key, "gpt-4o-mini"
    
    async def health_check(self) -> bool:
        """Check if LLM service is accessible"""
        try:
            provider, api_key, _ = await self._get_provider_and_key()
            return provider is not None and api_key is not None
        except Exception as e:
            logger.warning("LLM service health check failed", error=str(e))
            return False
    
    async def generate_analysis(self, domain: str, data: Dict[str, Any], user_id: Optional[UUID] = None) -> Optional[Dict[str, Any]]:
        """Generate domain analysis using LLM"""
        try:
            provider, api_key, model_name = await self._get_provider_and_key()
            if not provider or not api_key:
                logger.error("No LLM provider credentials available")
                return None
            
            # Prepare the analysis prompt
            prompt = self._build_analysis_prompt(domain, data)
            
            if provider == "gemini":
                result = await self._generate_with_gemini(prompt, domain, model_name)
            elif provider == "openai":
                result = await self._generate_with_openai(prompt, domain, api_key, model_name)
            else:
                logger.error(f"Unknown LLM provider: {provider}")
                return None
                
            if result:
                 await self.usage_tracking.track_usage(
                    user_id=user_id,
                    resource_type='llm',
                    operation='generate_analysis',
                    provider=provider,
                    model=model_name,
                    details={'domain': domain}
                )
            
            return result
            
        except Exception as e:
            logger.error("Failed to generate LLM analysis", domain=domain, error=str(e))
            return None
    
    async def generate_enhanced_analysis(self, domain: str, data: Dict[str, Any], user_id: Optional[UUID] = None) -> Optional[Dict[str, Any]]:
        """Generate enhanced domain analysis with backlink quality assessment"""
        logger.info("=== ENHANCED ANALYSIS CALLED ===", domain=domain)
        provider, api_key, model_name = await self._get_provider_and_key()
        if not provider or not api_key:
            logger.error("No LLM provider credentials available")
            raise ValueError("No LLM provider credentials available. Please configure LLM credentials in Supabase.")
        
        # Prepare the enhanced analysis prompt with detailed data
        prompt = self._build_enhanced_analysis_prompt(domain, data)
        logger.info("Enhanced prompt generated", domain=domain, prompt_length=len(prompt), prompt_preview=prompt[:500])
        
        if provider == "gemini":
            result = await self._generate_with_gemini(prompt, domain, model_name)
        elif provider == "openai":
            result = await self._generate_with_openai(prompt, domain, api_key, model_name)
        else:
            logger.error(f"Unknown LLM provider: {provider}")
            raise ValueError(f"Unknown LLM provider: {provider}")
        
        if not result:
            raise ValueError("LLM service returned no data")
            
        await self.usage_tracking.track_usage(
            user_id=user_id,
            resource_type='llm',
            operation='generate_enhanced_analysis',
            provider=provider,
            model=model_name,
            details={'domain': domain}
        )
        
        return result
    
    async def _generate_with_gemini(self, prompt: str, domain: str, model_name: str = 'gemini-2.0-flash-exp') -> Optional[Dict[str, Any]]:
        """Generate analysis using Gemini"""
        import google.generativeai as genai
        
        # Use provided model name, fallback if None
        model_name = model_name or 'gemini-2.0-flash-exp'
        
        genai.configure(api_key=self._gemini_key)
        model = genai.GenerativeModel(model_name)
        
        response = await asyncio.to_thread(
            model.generate_content,
            prompt
        )
        
        analysis_text = response.text
        return self._parse_llm_response(analysis_text, domain)
    
    async def _generate_with_openai(self, prompt: str, domain: str, api_key: str, model_name: str = 'gpt-4o-mini') -> Optional[Dict[str, Any]]:
        """Generate analysis using OpenAI"""
        import openai
        
        # Use provided model name, fallback if None
        model_name = model_name or 'gpt-4o-mini'
        
        client = openai.AsyncOpenAI(api_key=api_key)
        
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are an SEO expert analyzing domain data for domain buyers. You must respond with valid JSON matching the exact structure specified in the prompt."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        analysis_text = response.choices[0].message.content
        return self._parse_llm_response(analysis_text, domain)
    
    def _parse_llm_response(self, analysis_text: str, domain: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response into structured data"""
        import json
        import re
        
        # Log the raw response for debugging
        logger.info("Raw LLM response", domain=domain, response_length=len(analysis_text), response_preview=analysis_text[:500])
        
        # Look for JSON in the response
        json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
        if not json_match:
            logger.error("No JSON found in LLM response - LLM did not return valid JSON", domain=domain, response=analysis_text[:1000])
            raise ValueError(f"LLM did not return valid JSON. Response preview: {analysis_text[:500]}")
        
        try:
            analysis_data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON from LLM response", domain=domain, error=str(e), json_text=json_match.group()[:500])
            raise ValueError(f"LLM returned invalid JSON: {str(e)}")
        
        logger.info("Parsed JSON from LLM response", domain=domain, keys=list(analysis_data.keys()))
        
        # Validate that the response has the enhanced structure
        required_keys = ["buy_recommendation", "valuable_assets", "major_concerns", "content_strategy", "action_plan", "pros_and_cons"]
        missing_keys = [key for key in required_keys if key not in analysis_data]
        
        if missing_keys:
            logger.error("LLM response missing required enhanced fields", domain=domain, missing_keys=missing_keys, actual_keys=list(analysis_data.keys()))
            raise ValueError(f"LLM response missing required fields: {missing_keys}. This indicates the LLM is not following the enhanced prompt structure.")
        
        logger.info("LLM analysis generated successfully with enhanced structure", domain=domain)
        return analysis_data
    
    def _build_analysis_prompt(self, domain: str, data: Dict[str, Any]) -> str:
        """Build the analysis prompt for the LLM"""
        analytics = data.get("analytics", {})
        backlinks = data.get("backlinks", {})
        referring_domains = data.get("referring_domains", {})
        keywords = data.get("keywords", {})
        wayback = data.get("wayback", {})
        
        prompt = f"""
        Analyze the following domain data for {domain} and provide a comprehensive SEO analysis report.
        
        Domain Analytics:
        - Domain Authority (DataForSEO): {analytics.get('domain_rank', 'N/A')}
        - Organic Traffic: {analytics.get('organic_traffic', 'N/A')}
        - Total Referring Domains: {referring_domains.get('total_count', len(referring_domains.get('items', [])))}
        - Total Backlinks: {backlinks.get('backlinks_count', 'N/A')}
        
        IMPORTANT: If the domain has a significant number of backlinks (e.g., millions), this is a MAJOR SEO strength that should be highlighted prominently in the analysis. High backlink counts indicate strong domain authority and link equity.
        
        Top Keywords (showing first 10):
        {self._format_keywords(keywords.get('items', [])[:10])}
        
        Top Referring Domains (showing first 10):
        {self._format_backlinks(backlinks.get('items', [])[:10])}
        
        Detailed Referring Domains Analysis (up to 800 domains):
        {self._format_referring_domains(referring_domains.get('items', [])[:50])}
        
        CRITICAL: Analyze the quality of referring domains by examining:
        1. Domain authority distribution (DR scores)
        2. Diversity of referring domains
        3. Presence of high-authority domains (DR 70+)
        4. Geographic and topical diversity
        5. Anchor text patterns and relevance
        
        Historical Data:
        - Total Captures: {wayback.get('total_captures', 'N/A')}
        - First Capture Year: {wayback.get('first_capture_year', 'N/A')}
        - Last Capture: {wayback.get('last_capture_date', 'N/A')}
        
        Please provide a JSON response with the following structure:
        {{
            "good_highlights": [
                "List 5 strongest SEO assets and positive indicators"
            ],
            "bad_highlights": [
                "List 5 biggest SEO liabilities and concerns"
            ],
            "suggested_niches": [
                "List 3-5 content niches/topics that could be built on this domain"
            ],
            "advantages_disadvantages_table": [
                {{"type": "advantage", "description": "Description", "metric": "Supporting metric"}},
                {{"type": "disadvantage", "description": "Description", "metric": "Supporting metric"}}
            ],
            "summary": "Overall assessment of the domain's potential",
            "confidence_score": 0.85
        }}
        """
        
        return prompt
    
    def _build_enhanced_analysis_prompt(self, domain: str, data: Dict[str, Any]) -> str:
        """Build enhanced analysis prompt with detailed data and backlink quality assessment"""
        essential_metrics = data.get("essential_metrics", {})
        detailed_data = data.get("detailed_data", {})
        wayback_data = data.get("wayback_data", {})
        
        # Extract detailed data
        backlinks_data = detailed_data.get("backlinks", {})
        keywords_data = detailed_data.get("keywords", {})
        referring_domains_data = detailed_data.get("referring_domains", {})
        
        prompt = f"""
        You are an expert domain analyst. Analyze the following domain data for {domain} and provide a comprehensive SEO analysis specifically tailored for DOMAIN BUYERS looking to purchase expired or auctioned domains.
        
        You must respond with ONLY a valid JSON object. No text before or after the JSON.
        
        ESSENTIAL METRICS:
        - Domain Authority (DataForSEO): {essential_metrics.get('domain_rating', 'N/A')}
        - Organic Traffic: {essential_metrics.get('organic_traffic', 'N/A')}
        - Total Keywords: {essential_metrics.get('total_keywords', 'N/A')}
        - Total Backlinks: {essential_metrics.get('total_backlinks', 'N/A')}
        - Total Referring Domains: {essential_metrics.get('total_referring_domains', 'N/A')}
        
        DOMAIN BUYER FOCUS:
        - This analysis is specifically for people considering purchasing this domain
        - Focus on BUY/NO-BUY recommendations with specific reasoning
        - Provide actionable insights for building a new website on this domain
        - Highlight both opportunities and risks for domain buyers
        - Include specific examples of valuable backlinks and content opportunities
        
        DETAILED BACKLINKS ANALYSIS:
        **Total Backlinks: {backlinks_data.get('total_count', len(backlinks_data.get('items', [])))}** (This is the ACTUAL total count from the API)
        Sample of Top Backlinks (showing {len(backlinks_data.get('items', [])[:20])} out of {backlinks_data.get('total_count', 0)}):
        {self._format_detailed_backlinks(backlinks_data.get('items', [])[:20])}
        
        DETAILED KEYWORDS ANALYSIS:
        **Total Keywords: {keywords_data.get('total_count', len(keywords_data.get('items', [])))}** (This is the ACTUAL total count from the API)
        Sample of Top Keywords (showing {len(keywords_data.get('items', [])[:20])} out of {keywords_data.get('total_count', 0)}):
        {self._format_detailed_keywords(keywords_data.get('items', [])[:20])}
        
        DETAILED REFERRING DOMAINS ANALYSIS:
        **Total Referring Domains: {referring_domains_data.get('total_count', len(referring_domains_data.get('items', [])))}** (This is the ACTUAL total count from the API)
        Sample of Top Referring Domains (showing {len(referring_domains_data.get('items', [])[:30])} out of {referring_domains_data.get('total_count', 0)}):
        {self._format_detailed_referring_domains(referring_domains_data.get('items', [])[:30])}
        
        DOMAIN BUYER BACKLINK ANALYSIS:
        For domain buyers, analyze the backlink profile with focus on:
        1. **Valuable Backlinks**: Identify specific high-quality backlinks that provide SEO value (include domain names and DR scores)
        2. **Content Opportunities**: What topics/niches do the backlinks suggest for the new website?
        3. **Risk Assessment**: Are there toxic or spammy backlinks that could hurt the new website?
        4. **Link Equity Transfer**: How much SEO value will transfer to a new website on this domain?
        5. **Geographic Relevance**: Do backlinks suggest a specific geographic market or language?
        6. **Industry Relevance**: What industry or niche do the referring domains suggest?
        7. **Anchor Text Analysis**: What keywords are being targeted by existing backlinks?
        8. **Link Building Opportunities**: Which referring domains could be approached for new content?
        
        HISTORICAL DATA:
        - Total Captures: {wayback_data.get('total_captures', 'N/A')}
        - First Capture Year: {wayback_data.get('first_capture_year', 'N/A')}
        - Last Capture: {wayback_data.get('last_capture_date', 'N/A')}
        
        CRITICAL BACKLINK QUALITY ASSESSMENT:
        Analyze the backlink profile quality by examining:
        1. **Domain Authority Distribution**: Calculate percentage of backlinks from high-DR domains (70+)
        2. **Link Diversity**: Assess variety of referring domains and anchor text patterns
        3. **Link Relevance**: Evaluate topical relevance of referring domains to DataForSEO's business
        4. **Anchor Text Quality**: Analyze anchor text diversity, over-optimization, and keyword targeting
        5. **Link Types**: Identify dofollow vs nofollow ratios and link types
        6. **Geographic Distribution**: Assess international link diversity
        7. **Link Velocity**: Analyze backlink acquisition patterns over time
        8. **Toxic Link Detection**: Identify potentially harmful or spammy backlinks
        9. **Competitor Analysis**: Compare backlink profile to industry standards
        10. **Link Equity Assessment**: Evaluate the overall value and authority transfer potential
        
        QUALITY SCORING CRITERIA:
        - **Excellent (9-10)**: High-DR domains (80+), relevant anchor text, diverse sources
        - **Good (7-8)**: Medium-DR domains (50-79), mostly relevant, good diversity
        - **Fair (5-6)**: Mixed quality, some irrelevant links, moderate diversity
        - **Poor (3-4)**: Low-DR domains (30-), many irrelevant links, limited diversity
        - **Toxic (1-2)**: Spammy domains, over-optimized anchors, suspicious patterns
        
        ANALYSIS REQUIREMENTS:
        - Provide comprehensive analysis based on complete detailed data
        - Include specific backlink quality metrics and insights
        - Provide comprehensive keyword analysis
        - Include actionable recommendations based on detailed findings
        - Provide confidence in analysis based on complete data availability
        
        Return your analysis as a JSON object with this structure:
        {{
            "buy_recommendation": {{
                "recommendation": "BUY or NO-BUY or CAUTION",
                "confidence": 0.85,
                "reasoning": "Detailed reasoning for the recommendation",
                "risk_level": "low/medium/high",
                "potential_value": "low/medium/high"
            }},
            "valuable_assets": [
                "List specific valuable SEO assets with examples"
            ],
            "major_concerns": [
                "List specific concerns with examples"
            ],
            "content_strategy": {{
                "primary_niche": "Main content niche",
                "secondary_niches": ["Secondary niche 1", "Secondary niche 2"],
                "first_articles": ["Article topic 1", "Article topic 2"],
                "target_keywords": ["Keyword 1", "Keyword 2"]
            }},
            "action_plan": {{
                "immediate_actions": ["Immediate action 1", "Immediate action 2"],
                "first_month": ["First month action 1", "First month action 2"],
                "long_term_strategy": ["Long term strategy 1", "Long term strategy 2"]
            }},
            "pros_and_cons": [
                {{"type": "pro", "description": "Specific advantage", "impact": "high/medium/low", "example": "Specific example"}},
                {{"type": "con", "description": "Specific disadvantage", "impact": "high/medium/low", "example": "Specific example"}}
            ],
            "summary": "Comprehensive summary with specific reasoning",
            "confidence_score": 0.85
        }}
        """
        
        return prompt
    
    def _format_detailed_backlinks(self, backlinks: List[Dict[str, Any]]) -> str:
        """Format detailed backlinks data for the prompt"""
        if not backlinks:
            return "No detailed backlinks data available"
        
        formatted = []
        for bl in backlinks:
            url_from = bl.get('url_from') or bl.get('url') or 'Not specified'
            domain_from = bl.get('domain_from') or bl.get('domain') or 'Not specified'
            domain_rank = bl.get('domain_from_rank') or bl.get('domain_rank') or 'Not specified'
            anchor = bl.get('anchor') or bl.get('anchor_text') or 'Not specified'
            first_seen = bl.get('first_seen') or 'Not specified'
            link_type = bl.get('link_type') or bl.get('type') or 'dofollow'
            
            formatted.append(f"- URL: {url_from}")
            formatted.append(f"  Domain: {domain_from} (DR: {domain_rank})")
            formatted.append(f"  Anchor: {anchor}")
            formatted.append(f"  First Seen: {first_seen}")
            formatted.append(f"  Link Type: {link_type}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def _format_detailed_keywords(self, keywords: List[Dict[str, Any]]) -> str:
        """Format detailed keywords data for the prompt"""
        if not keywords:
            return "No detailed keywords data available"
        
        formatted = []
        for kw in keywords:
            formatted.append(f"- {kw.get('keyword', 'N/A')}")
            formatted.append(f"  Position: {kw.get('position', 'N/A')}")
            formatted.append(f"  Search Volume: {kw.get('search_volume', 'N/A')}")
            formatted.append(f"  CPC: {kw.get('cpc', 'N/A')}")
            formatted.append(f"  Competition: {kw.get('competition', 'N/A')}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def _format_detailed_referring_domains(self, referring_domains: List[Dict[str, Any]]) -> str:
        """Format detailed referring domains data for the prompt"""
        if not referring_domains:
            return "No detailed referring domains data available"
        
        formatted = []
        for rd in referring_domains:
            domain_from = rd.get('domain_from') or rd.get('domain') or 'Not specified'
            domain_rank = rd.get('domain_from_rank') or rd.get('domain_rank') or 'Not specified'
            backlinks_count = rd.get('backlinks_count') or rd.get('backlinks') or 'Not specified'
            first_seen = rd.get('first_seen') or 'Not specified'
            last_seen = rd.get('last_seen') or 'Not specified'
            
            formatted.append(f"- {domain_from}")
            formatted.append(f"  DR: {domain_rank}")
            formatted.append(f"  Backlinks: {backlinks_count}")
            formatted.append(f"  First Seen: {first_seen}")
            formatted.append(f"  Last Seen: {last_seen}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def calculate_backlink_quality_score(self, backlinks_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive backlink quality score"""
        try:
            items = backlinks_data.get("items", [])
            if not items:
                return {
                    "overall_quality_score": 0.0,
                    "high_dr_percentage": 0.0,
                    "link_diversity_score": 0.0,
                    "relevance_score": 0.0,
                    "velocity_score": 0.0,
                    "geographic_diversity": 0.0,
                    "anchor_text_diversity": 0.0
                }
            
            # Calculate high DR percentage (DR 70+)
            high_dr_count = sum(1 for bl in items if bl.get('domain_from_rank', 0) >= 70)
            high_dr_percentage = (high_dr_count / len(items)) * 100 if items else 0
            
            # Calculate link diversity (unique domains)
            unique_domains = len(set(bl.get('domain_from', '') for bl in items))
            link_diversity_score = min(10.0, (unique_domains / len(items)) * 10) if items else 0
            
            # Calculate anchor text diversity
            anchor_texts = [bl.get('anchor', '') for bl in items if bl.get('anchor')]
            unique_anchors = len(set(anchor_texts))
            anchor_text_diversity = min(10.0, (unique_anchors / len(anchor_texts)) * 10) if anchor_texts else 0
            
            # Calculate average DR score
            dr_scores = [bl.get('domain_from_rank', 0) for bl in items if bl.get('domain_from_rank')]
            avg_dr = sum(dr_scores) / len(dr_scores) if dr_scores else 0
            relevance_score = min(10.0, avg_dr / 10)  # Normalize to 0-10 scale
            
            # Calculate velocity score (based on first_seen dates)
            first_seen_dates = [bl.get('first_seen') for bl in items if bl.get('first_seen')]
            if first_seen_dates:
                # Simple velocity calculation - more recent links = higher score
                recent_links = sum(1 for date in first_seen_dates if '2023' in str(date) or '2024' in str(date))
                velocity_score = min(10.0, (recent_links / len(first_seen_dates)) * 10)
            else:
                velocity_score = 5.0  # Neutral score if no dates
            
            # Geographic diversity (simplified - would need country data)
            geographic_diversity = 7.0  # Placeholder - would need actual country data
            
            # Overall quality score (weighted average)
            overall_quality_score = (
                (high_dr_percentage / 10) * 0.25 +
                (link_diversity_score / 10) * 0.20 +
                (relevance_score / 10) * 0.20 +
                (anchor_text_diversity / 10) * 0.15 +
                (velocity_score / 10) * 0.10 +
                (geographic_diversity / 10) * 0.10
            ) * 10
            
            return {
                "overall_quality_score": round(overall_quality_score, 1),
                "high_dr_percentage": round(high_dr_percentage, 1),
                "link_diversity_score": round(link_diversity_score, 1),
                "relevance_score": round(relevance_score, 1),
                "velocity_score": round(velocity_score, 1),
                "geographic_diversity": round(geographic_diversity, 1),
                "anchor_text_diversity": round(anchor_text_diversity, 1),
                "total_backlinks": len(items),
                "unique_domains": unique_domains,
                "unique_anchors": unique_anchors,
                "avg_dr_score": round(avg_dr, 1)
            }
            
        except Exception as e:
            logger.error("Failed to calculate backlink quality score", error=str(e))
            return {
                "overall_quality_score": 0.0,
                "high_dr_percentage": 0.0,
                "link_diversity_score": 0.0,
                "relevance_score": 0.0,
                "velocity_score": 0.0,
                "geographic_diversity": 0.0,
                "anchor_text_diversity": 0.0
            }
    
    def calculate_comprehensive_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive analysis metrics"""
        try:
            essential_metrics = data.get("essential_metrics", {})
            detailed_data = data.get("detailed_data", {})
            
            # Backlink quality metrics
            backlinks_data = detailed_data.get("backlinks", {})
            backlink_quality = self.calculate_backlink_quality_score(backlinks_data)
            
            # Keyword metrics
            keywords_data = detailed_data.get("keywords", {})
            keyword_items = keywords_data.get("items", [])
            
            # Calculate keyword metrics
            total_keywords = len(keyword_items)
            top_10_keywords = keyword_items[:10]
            avg_position = sum(kw.get('position', 0) for kw in top_10_keywords) / len(top_10_keywords) if top_10_keywords else 0
            total_search_volume = sum(kw.get('search_volume', 0) for kw in keyword_items)
            
            # Referring domains metrics
            referring_domains_data = detailed_data.get("referring_domains", {})
            referring_domains_items = referring_domains_data.get("items", [])
            
            # Calculate referring domains metrics
            total_referring_domains = len(referring_domains_items)
            avg_dr_referring = sum(rd.get('domain_from_rank', 0) for rd in referring_domains_items) / len(referring_domains_items) if referring_domains_items else 0
            
            # Overall domain health score
            domain_rank = essential_metrics.get('domain_rating', 0)  # This is actually domain_rank now
            organic_traffic = essential_metrics.get('organic_traffic', 0)
            
            # Calculate overall health score
            health_score = (
                (domain_rank / 100) * 0.30 +
                (backlink_quality['overall_quality_score'] / 10) * 0.25 +
                (min(10.0, total_keywords / 100) / 10) * 0.20 +
                (min(10.0, total_referring_domains / 50) / 10) * 0.15 +
                (min(10.0, organic_traffic / 10000) / 10) * 0.10
            ) * 10
            
            return {
                "overall_health_score": round(health_score, 1),
                "backlink_quality": backlink_quality,
                "keyword_metrics": {
                    "total_keywords": total_keywords,
                    "avg_position_top_10": round(avg_position, 1),
                    "total_search_volume": total_search_volume,
                    "keyword_diversity": len(set(kw.get('keyword', '') for kw in keyword_items))
                },
                "referring_domains_metrics": {
                    "total_referring_domains": total_referring_domains,
                    "avg_dr_score": round(avg_dr_referring, 1),
                    "high_dr_domains": sum(1 for rd in referring_domains_items if rd.get('domain_from_rank', 0) >= 70)
                },
                "domain_metrics": {
                    "domain_rating": domain_rank,  # This is actually domain_rank now
                    "organic_traffic": organic_traffic,
                    "traffic_quality_score": min(10.0, organic_traffic / 1000)
                }
            }
            
        except Exception as e:
            logger.error("Failed to calculate comprehensive metrics", error=str(e))
            return {
                "overall_health_score": 0.0,
                "backlink_quality": {},
                "keyword_metrics": {},
                "referring_domains_metrics": {},
                "domain_metrics": {}
            }
    
    def _format_keywords(self, keywords: List[Dict[str, Any]]) -> str:
        """Format keywords data for the prompt"""
        if not keywords:
            return "No keywords data available"
        
        formatted = []
        for kw in keywords:
            formatted.append(f"- {kw.get('keyword', 'N/A')} (Rank: {kw.get('rank_group', 'N/A')}, Volume: {kw.get('search_volume', 'N/A')})")
        
        return "\n".join(formatted)
    
    def _format_backlinks(self, backlinks: List[Dict[str, Any]]) -> str:
        """Format backlinks data for the prompt"""
        if not backlinks:
            return "No backlinks data available"
        
        formatted = []
        for bl in backlinks:
            formatted.append(f"- {bl.get('domain', 'N/A')} (DR: {bl.get('domain_rank', 'N/A')}, Backlinks: {bl.get('backlinks_count', 'N/A')})")
        
        return "\n".join(formatted)
    
    def _format_referring_domains(self, referring_domains: List[Dict[str, Any]]) -> str:
        """Format referring domains data for the prompt"""
        if not referring_domains:
            return "No referring domains data available"
        
        formatted = []
        for rd in referring_domains:
            formatted.append(f"- {rd.get('domain', 'N/A')} (DR: {rd.get('domain_rank', 'N/A')}, Backlinks: {rd.get('backlinks_count', 'N/A')}, First Seen: {rd.get('first_seen', 'N/A')})")
        
        return "\n".join(formatted)
    
    def _parse_text_response(self, text: str) -> Dict[str, Any]:
        """Parse text response into structured data"""
        return {
            "good_highlights": ["Analysis generated from text response"],
            "bad_highlights": ["Analysis generated from text response"],
            "suggested_niches": ["Analysis generated from text response"],
            "advantages_disadvantages_table": [],
            "summary": text,
            "confidence_score": 0.5
        }
    
    async def generate_development_plan(self, report) -> Dict[str, Any]:
        """Generate a development plan based on domain analysis data"""
        try:
            provider, api_key, model_name = await self._get_provider_and_key()
            if not provider or not api_key:
                logger.error("No LLM provider credentials available")
                return self._get_default_development_plan()
            
            # Build development plan prompt
            prompt = self._build_development_plan_prompt(report)
            
            if provider == "gemini":
                return await self._generate_with_gemini(prompt, api_key, model_name)
            else:
                return await self._generate_with_openai(prompt, api_key, api_key, model_name)
                
        except Exception as e:
            logger.error("Failed to generate development plan", error=str(e))
            return self._get_default_development_plan()
    
    def _build_development_plan_prompt(self, report) -> str:
        """Build prompt for development plan generation"""
        domain = report.domain_name
        metrics = report.data_for_seo_metrics
        
        # Get detailed data from database
        try:
            from services.database import DatabaseService
            import asyncio
            
            db = DatabaseService()
            
            # Get actual keyword and backlink data (await the async calls)
            keywords_data = asyncio.run(db.get_detailed_data(domain, 'keywords')) or {'items': []}
            backlinks_data = asyncio.run(db.get_detailed_data(domain, 'backlinks')) or {'items': []}
            referring_domains_data = asyncio.run(db.get_detailed_data(domain, 'referring_domains')) or {'items': []}
            
            logger.info(f"Retrieved data for development plan", 
                       keywords_count=len(keywords_data.get('items', [])),
                       backlinks_count=len(backlinks_data.get('items', [])),
                       referring_domains_count=len(referring_domains_data.get('items', [])))
        except Exception as e:
            logger.error("Failed to get detailed data for development plan", error=str(e))
            # Fallback to empty data
            keywords_data = {'items': []}
            backlinks_data = {'items': []}
            referring_domains_data = {'items': []}
        
        # Extract metrics safely
        dr = getattr(metrics, 'domain_rating_dr', None) if metrics else None
        traffic = getattr(metrics, 'organic_traffic_est', None) if metrics else None
        backlinks = getattr(metrics, 'total_backlinks', None) if metrics else None
        keywords = getattr(metrics, 'total_keywords', None) if metrics else None
        referring_domains = getattr(metrics, 'total_referring_domains', None) if metrics else None
        
        # Analyze the data to extract specific content opportunities
        content_opportunities = self._analyze_content_opportunities(keywords_data.get('items', []), backlinks_data.get('items', []))
        specific_article_ideas = self._generate_specific_article_ideas(keywords_data.get('items', []))
        tool_opportunities = self._identify_tool_opportunities(keywords_data.get('items', []))
        partnership_opportunities = self._identify_partnership_opportunities(backlinks_data.get('items', []))
        
        prompt = f"""
You are an expert SEO strategist and domain development consultant. Based on the comprehensive analysis data for {domain}, create a detailed development plan to increase organic traffic and improve domain authority.

DOMAIN ANALYSIS SUMMARY:
- Domain Rating (DR): {dr or 'N/A'}
- Organic Traffic Estimate: {traffic or 'N/A'}
- Total Backlinks: {backlinks or 'N/A'}
- Total Keywords: {keywords or 'N/A'}
- Total Referring Domains: {referring_domains or 'N/A'}

SPECIFIC CONTENT OPPORTUNITIES IDENTIFIED:
{content_opportunities}

SPECIFIC ARTICLE IDEAS BASED ON SUCCESSFUL KEYWORDS:
{specific_article_ideas}

TOOL OPPORTUNITIES BASED ON KEYWORD ANALYSIS:
{tool_opportunities}

PARTNERSHIP OPPORTUNITIES BASED ON EXISTING BACKLINKS:
{partnership_opportunities}

CURRENT KEYWORD PERFORMANCE (analyze these for content opportunities):
{self._format_keywords_for_development(keywords_data.get('items', [])[:20])}

CURRENT BACKLINK PROFILE (analyze these for content partnership opportunities):
{self._format_backlinks_for_development(backlinks_data.get('items', [])[:20])}

CURRENT REFERRING DOMAINS (analyze these for partnership opportunities):
{self._format_referring_domains_for_development(referring_domains_data.get('items', [])[:20])}

ANALYSIS INSTRUCTIONS:
- Look at the EXACT keywords that are ranking well and suggest specific article topics based on them
- Look at the EXACT backlink sources and suggest similar content opportunities
- Suggest specific tools, calculators, or resources to add to the website based on successful keywords
- Provide exact article titles and content ideas based on the data above
- Suggest how to leverage existing successful backlink sources for new content partnerships

TASK: Create a DOMAIN BUYER DEVELOPMENT PLAN that shows IMMEDIATE OPPORTUNITIES:

1. **Domain Potential Overview**: What this domain could become based on existing assets
2. **Immediate Opportunities**: 3-5 specific things the buyer can do RIGHT NOW
3. **Quick Win Strategies**: Low-effort, high-impact actions with:
   - Clear titles and descriptions
   - Priority level (high/medium/low)
   - Effort estimation (low/medium/high)
   - Expected impact (low/medium/high)
   - Timeline (e.g., "1-2 weeks", "1 month")
   - Step-by-step implementation guide
   - Specific content ideas based on existing data
   - Expected traffic increase

4. **Domain Development Roadmap**: What the domain could become in 6-12 months
5. **Success Metrics**: Specific KPIs to track progress

CRITICAL REQUIREMENTS - BE VERY SPECIFIC:
- **ANALYZE THE EXACT KEYWORDS**: Look at the specific keywords provided above and suggest exact article titles based on them
- **ANALYZE THE EXACT BACKLINKS**: Look at the specific backlink sources provided above and suggest similar content opportunities
- **SUGGEST SPECIFIC TOOLS**: Based on successful keywords, suggest exact tools, calculators, or resources to add to the website
- **PROVIDE EXACT ARTICLE TITLES**: Give specific, actionable article titles based on the data
- **SUGGEST CONTENT PARTNERSHIPS**: Based on existing backlink sources, suggest specific outreach opportunities
- **LEVERAGE EXISTING SUCCESS**: Build on the exact keywords and backlinks that are already working

REQUIRED ANALYSIS - BE VERY SPECIFIC:
1. **EXACT BLOG POST IDEAS**: For each successful keyword, provide 3-5 specific blog post titles that could be written
2. **SPECIFIC TOOLS TO BUILD**: Based on successful keywords, suggest exact tools/calculators with specific features
3. **CONTENT SERIES IDEAS**: Group related keywords into multi-part content series with specific titles
4. **PARTNERSHIP OPPORTUNITIES**: Based on existing backlink sources, suggest specific websites to reach out to
5. **IMMEDIATE ACTION ITEMS**: Provide 5-10 specific, actionable content ideas that can be started immediately

REQUIRED OUTPUT FORMAT:
For each strategy, provide:
- **Specific Blog Post Titles**: "How to Use DataForSEO API for [Specific Use Case]", "Complete Guide to [Specific Tool]"
- **Exact Tools to Build**: "Keyword Difficulty Calculator", "SERP Position Tracker", "Backlink Analyzer"
- **Content Series Ideas**: "DataForSEO API Tutorial Series", "SEO Tools Comparison Series"
- **Specific Outreach Targets**: Based on existing backlink sources, suggest exact websites to contact

EXAMPLE OF SPECIFIC SUGGESTIONS:
- If "API for SEO" keywords work → suggest "Complete DataForSEO API Tutorial for Beginners", "How to Build SEO Tools with DataForSEO API", "DataForSEO vs Ahrefs API: Complete Comparison"
- If "keyword research" keywords work → suggest building "Free Keyword Difficulty Checker", "Long-tail Keyword Generator", "Competitor Keyword Analyzer"
- If backlinks from "seotools.com" → suggest reaching out to "ahrefs.com", "semrush.com", "moz.com" for guest posting
- If "technical SEO" keywords work → suggest "Technical SEO Audit Tool", "Core Web Vitals Checker", "Schema Markup Validator"

PROVIDE SPECIFIC, ACTIONABLE CONTENT IDEAS THAT THE USER CAN START IMMEDIATELY!

CRITICAL: This is for DOMAIN BUYERS who need IMMEDIATE ACTIONABLE INSIGHTS!

Focus on providing:
1. **IMMEDIATE OPPORTUNITIES**: What can be built/developed RIGHT NOW based on existing data
2. **SPECIFIC CONTENT IDEAS**: Exact blog posts, tools, or services that leverage existing backlinks/keywords
3. **QUICK WINS**: Low-effort, high-impact actions the buyer can take immediately
4. **DOMAIN POTENTIAL**: What this domain could become based on its current assets

EXAMPLES OF SPECIFIC INSIGHTS TO PROVIDE:
- "You have backlinks from food.com → Start a food blog about [specific cuisine]"
- "Keywords show 'pet training' success → Build a pet training course or tool"
- "Backlinks from tech blogs → Create developer tutorials or tools"
- "High 'DIY' keyword traffic → Launch a DIY project marketplace"
- "Travel-related backlinks → Start a travel booking service or blog"

BE SPECIFIC ABOUT WHAT THE BUYER CAN DO IMMEDIATELY!

RESPONSE FORMAT: Return a JSON object with the following structure:
{{
  "title": "Domain Development Plan for {domain}",
  "description": "Comprehensive strategy to increase organic traffic and domain authority",
  "strategies": [
    {{
      "id": "strategy_1",
      "title": "Strategy Title",
      "description": "Detailed description of the strategy",
      "priority": "high|medium|low",
      "estimated_effort": "low|medium|high",
      "expected_impact": "low|medium|high",
      "timeline": "2-4 weeks",
      "steps": ["Step 1", "Step 2", "Step 3"],
      "keywords": ["keyword1", "keyword2"],
      "expected_traffic_increase": "20-30% increase in 3 months"
    }}
  ],
  "timeline": [
    {{
      "phase": "Phase 1: Foundation",
      "duration": "4-6 weeks",
      "focus": "Content optimization and technical improvements"
    }}
  ],
  "success_metrics": [
    "Organic traffic increase by X%",
    "Domain Rating improvement",
    "Keyword ranking improvements"
  ]
}}

Focus on creating actionable, data-driven strategies that will genuinely help {domain} grow its organic traffic and authority.
"""
        return prompt
    
    def _format_keywords_for_development(self, keywords: List[Dict[str, Any]]) -> str:
        """Format keywords for development plan context"""
        if not keywords:
            return "No keyword data available"
        
        formatted = []
        formatted.append("TOP PERFORMING KEYWORDS (analyze these for content opportunities):")
        formatted.append("")
        
        # Sort keywords by rank (best performing first)
        sorted_keywords = sorted(keywords, key=lambda x: x.get('rank_group', 999))
        
        for kw in sorted_keywords[:15]:  # Top 15 keywords
            keyword = kw.get('keyword', 'N/A')
            rank = kw.get('rank_group', 'N/A')
            volume = kw.get('search_volume', 'N/A')
            cpc = kw.get('cpc', 'N/A')
            competition = kw.get('competition_level', 'N/A')
            
            # Add context about what this keyword suggests
            context = ""
            if "api" in keyword.lower():
                context = " → Suggests API-related content opportunities"
            elif "tool" in keyword.lower() or "software" in keyword.lower():
                context = " → Suggests tool/software content opportunities"
            elif "guide" in keyword.lower() or "tutorial" in keyword.lower():
                context = " → Suggests educational content opportunities"
            elif "seo" in keyword.lower():
                context = " → Suggests SEO-focused content opportunities"
            elif "calculator" in keyword.lower() or "checker" in keyword.lower():
                context = " → Suggests tool development opportunities"
            elif "analysis" in keyword.lower() or "audit" in keyword.lower():
                context = " → Suggests analytical content opportunities"
            
            # Add specific content suggestions based on keyword
            content_suggestion = self._get_keyword_content_suggestion(keyword)
            if content_suggestion:
                context += f" → {content_suggestion}"
            
            formatted.append(f"- {keyword} (Position: {rank}, Volume: {volume}, CPC: {cpc}, Competition: {competition}){context}")
        
        return "\n".join(formatted)
    
    def _format_backlinks_for_development(self, backlinks: List[Dict[str, Any]]) -> str:
        """Format backlinks for development plan context"""
        if not backlinks:
            return "No backlink data available"
        
        formatted = []
        formatted.append("TOP REFERRING DOMAINS (analyze these for content partnership opportunities):")
        formatted.append("")
        
        # Sort backlinks by domain rank (highest quality first)
        sorted_backlinks = sorted(backlinks, key=lambda x: x.get('domain_rank', 0), reverse=True)
        
        for bl in sorted_backlinks[:15]:  # Top 15 backlinks
            domain = bl.get('domain', 'N/A')
            dr = bl.get('domain_rank', 'N/A')
            count = bl.get('backlinks_count', 'N/A')
            anchor_text = bl.get('anchor_text', 'N/A')
            
            # Add context about what this backlink suggests
            context = ""
            if "blog" in domain.lower() or "news" in domain.lower():
                context = " → Suggests content marketing opportunities"
            elif "tool" in domain.lower() or "software" in domain.lower():
                context = " → Suggests tool integration opportunities"
            elif "seo" in domain.lower() or "marketing" in domain.lower():
                context = " → Suggests industry partnership opportunities"
            elif "developer" in domain.lower() or "tech" in domain.lower():
                context = " → Suggests developer-focused content opportunities"
            elif "forum" in domain.lower() or "community" in domain.lower():
                context = " → Suggests community engagement opportunities"
            
            # Add specific partnership suggestions
            partnership_suggestion = self._get_backlink_partnership_suggestion(domain, anchor_text)
            if partnership_suggestion:
                context += f" → {partnership_suggestion}"
            
            formatted.append(f"- {domain} (DR: {dr}, Links: {count}, Anchor: {anchor_text}){context}")
        
        return "\n".join(formatted)
    
    def _format_referring_domains_for_development(self, referring_domains: List[Dict[str, Any]]) -> str:
        """Format referring domains for development plan context"""
        if not referring_domains:
            return "No referring domain data available"
        
        formatted = []
        formatted.append("TOP REFERRING DOMAINS (analyze these for content partnership opportunities):")
        formatted.append("")
        
        for rd in referring_domains[:15]:  # Top 15 referring domains
            domain = rd.get('domain', 'N/A')
            dr = rd.get('domain_rank', 'N/A')
            backlinks = rd.get('backlinks_count', 'N/A')
            
            # Add context about what this referring domain suggests
            context = ""
            if "blog" in domain.lower() or "news" in domain.lower():
                context = " → Suggests content marketing opportunities"
            elif "tool" in domain.lower() or "software" in domain.lower():
                context = " → Suggests tool integration opportunities"
            elif "seo" in domain.lower() or "marketing" in domain.lower():
                context = " → Suggests industry partnership opportunities"
            elif "developer" in domain.lower() or "tech" in domain.lower():
                context = " → Suggests developer-focused content opportunities"
            
            formatted.append(f"- {domain} (DR: {dr}, Backlinks: {backlinks}){context}")
        
        return "\n".join(formatted)
    
    def _analyze_content_opportunities(self, keywords: List[Dict[str, Any]], backlinks: List[Dict[str, Any]]) -> str:
        """Analyze keywords and backlinks to identify specific content opportunities"""
        if not keywords and not backlinks:
            return "No data available for content opportunity analysis"
        
        opportunities = []
        opportunities.append("CONTENT OPPORTUNITY ANALYSIS:")
        opportunities.append("")
        
        # Analyze keyword patterns
        if keywords:
            keyword_themes = self._extract_keyword_themes(keywords[:20])
            opportunities.append("KEYWORD THEMES IDENTIFIED:")
            for theme, examples in keyword_themes.items():
                opportunities.append(f"- {theme}: {', '.join(examples[:3])}")
            opportunities.append("")
        
        # Analyze backlink patterns
        if backlinks:
            backlink_themes = self._extract_backlink_themes(backlinks[:20])
            opportunities.append("BACKLINK SOURCE THEMES:")
            for theme, examples in backlink_themes.items():
                opportunities.append(f"- {theme}: {', '.join(examples[:3])}")
            opportunities.append("")
        
        # Suggest content clusters
        content_clusters = self._suggest_content_clusters(keywords[:15], backlinks[:15])
        opportunities.append("SUGGESTED CONTENT CLUSTERS:")
        for cluster in content_clusters:
            opportunities.append(f"- {cluster}")
        
        return "\n".join(opportunities)
    
    def _generate_specific_article_ideas(self, keywords: List[Dict[str, Any]]) -> str:
        """Generate specific article ideas based on successful keywords"""
        if not keywords:
            return "No keyword data available for article ideas"
        
        ideas = []
        ideas.append("SPECIFIC ARTICLE IDEAS BASED ON SUCCESSFUL KEYWORDS:")
        ideas.append("")
        
        # Group keywords by theme and generate specific titles
        keyword_groups = self._group_keywords_by_theme(keywords[:20])
        
        for theme, kw_list in keyword_groups.items():
            ideas.append(f"{theme.upper()} ARTICLES:")
            for i, kw in enumerate(kw_list[:5]):  # Top 5 per theme
                keyword = kw.get('keyword', '')
                rank = kw.get('rank_group', 'N/A')
                volume = kw.get('search_volume', 'N/A')
                
                # Generate specific article title based on keyword
                article_title = self._generate_article_title(keyword, theme)
                ideas.append(f"- \"{article_title}\" (Keyword: {keyword}, Position: {rank}, Volume: {volume})")
            ideas.append("")
        
        return "\n".join(ideas)
    
    def _identify_tool_opportunities(self, keywords: List[Dict[str, Any]]) -> str:
        """Identify specific tool opportunities based on keyword analysis"""
        if not keywords:
            return "No keyword data available for tool opportunities"
        
        tools = []
        tools.append("TOOL OPPORTUNITIES BASED ON KEYWORD ANALYSIS:")
        tools.append("")
        
        # Look for tool-related keywords
        tool_keywords = [kw for kw in keywords if any(word in kw.get('keyword', '').lower() 
                      for word in ['tool', 'calculator', 'checker', 'analyzer', 'generator', 'converter'])]
        
        if tool_keywords:
            tools.append("EXISTING TOOL-RELATED KEYWORDS:")
            for kw in tool_keywords[:10]:
                keyword = kw.get('keyword', '')
                rank = kw.get('rank_group', 'N/A')
                tools.append(f"- {keyword} (Position: {rank})")
            tools.append("")
        
        # Suggest specific tools based on keyword themes
        tool_suggestions = self._suggest_tools_from_keywords(keywords[:20])
        tools.append("SUGGESTED TOOLS TO BUILD:")
        for tool in tool_suggestions:
            tools.append(f"- {tool}")
        
        return "\n".join(tools)
    
    def _identify_partnership_opportunities(self, backlinks: List[Dict[str, Any]]) -> str:
        """Identify partnership opportunities based on existing backlinks"""
        if not backlinks:
            return "No backlink data available for partnership opportunities"
        
        partnerships = []
        partnerships.append("PARTNERSHIP OPPORTUNITIES BASED ON EXISTING BACKLINKS:")
        partnerships.append("")
        
        # Analyze backlink sources for partnership potential
        high_dr_sources = [bl for bl in backlinks if bl.get('domain_rank', 0) > 50]
        
        if high_dr_sources:
            partnerships.append("HIGH-QUALITY BACKLINK SOURCES (Potential Partners):")
            for bl in high_dr_sources[:10]:
                domain = bl.get('domain', 'N/A')
                dr = bl.get('domain_rank', 'N/A')
                partnerships.append(f"- {domain} (DR: {dr}) - Potential for guest posting or collaboration")
            partnerships.append("")
        
        # Suggest specific outreach targets
        outreach_targets = self._suggest_outreach_targets(backlinks[:20])
        partnerships.append("SUGGESTED OUTREACH TARGETS:")
        for target in outreach_targets:
            partnerships.append(f"- {target}")
        
        return "\n".join(partnerships)
    
    def _extract_keyword_themes(self, keywords: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Extract themes from keywords"""
        themes = {}
        
        for kw in keywords:
            keyword = kw.get('keyword', '').lower()
            
            # Define theme patterns
            if any(word in keyword for word in ['api', 'integration', 'developer']):
                themes.setdefault('Developer/API Content', []).append(kw.get('keyword', ''))
            elif any(word in keyword for word in ['tool', 'calculator', 'checker']):
                themes.setdefault('Tools & Calculators', []).append(kw.get('keyword', ''))
            elif any(word in keyword for word in ['guide', 'tutorial', 'how to']):
                themes.setdefault('Educational Content', []).append(kw.get('keyword', ''))
            elif any(word in keyword for word in ['seo', 'marketing', 'optimization']):
                themes.setdefault('SEO & Marketing', []).append(kw.get('keyword', ''))
            elif any(word in keyword for word in ['analysis', 'report', 'audit']):
                themes.setdefault('Analysis & Reporting', []).append(kw.get('keyword', ''))
            else:
                themes.setdefault('General Content', []).append(kw.get('keyword', ''))
        
        return themes
    
    def _extract_backlink_themes(self, backlinks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Extract themes from backlink sources"""
        themes = {}
        
        for bl in backlinks:
            domain = bl.get('domain', '').lower()
            
            # Define theme patterns
            if any(word in domain for word in ['blog', 'news', 'media']):
                themes.setdefault('Content & Media Sites', []).append(bl.get('domain', ''))
            elif any(word in domain for word in ['tool', 'software', 'app']):
                themes.setdefault('Tool & Software Sites', []).append(bl.get('domain', ''))
            elif any(word in domain for word in ['seo', 'marketing', 'digital']):
                themes.setdefault('SEO & Marketing Sites', []).append(bl.get('domain', ''))
            elif any(word in domain for word in ['tech', 'developer', 'programming']):
                themes.setdefault('Tech & Developer Sites', []).append(bl.get('domain', ''))
            else:
                themes.setdefault('Other Sites', []).append(bl.get('domain', ''))
        
        return themes
    
    def _suggest_content_clusters(self, keywords: List[Dict[str, Any]], backlinks: List[Dict[str, Any]]) -> List[str]:
        """Suggest content clusters based on keywords and backlinks"""
        clusters = []
        
        # Analyze keyword themes
        keyword_themes = self._extract_keyword_themes(keywords)
        
        for theme, examples in keyword_themes.items():
            if len(examples) >= 3:  # Only suggest clusters with enough content
                clusters.append(f"{theme} Content Series (based on {len(examples)} related keywords)")
        
        return clusters[:5]  # Top 5 clusters
    
    def _group_keywords_by_theme(self, keywords: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group keywords by theme for article generation"""
        groups = {}
        
        for kw in keywords:
            keyword = kw.get('keyword', '').lower()
            
            if any(word in keyword for word in ['api', 'integration', 'developer']):
                groups.setdefault('Developer/API Content', []).append(kw)
            elif any(word in keyword for word in ['tool', 'calculator', 'checker']):
                groups.setdefault('Tools & Calculators', []).append(kw)
            elif any(word in keyword for word in ['guide', 'tutorial', 'how to']):
                groups.setdefault('Educational Content', []).append(kw)
            elif any(word in keyword for word in ['seo', 'marketing', 'optimization']):
                groups.setdefault('SEO & Marketing', []).append(kw)
            else:
                groups.setdefault('General Content', []).append(kw)
        
        return groups
    
    def _generate_article_title(self, keyword: str, theme: str) -> str:
        """Generate specific article title based on keyword and theme"""
        keyword_lower = keyword.lower()
        
        # Generate titles based on keyword patterns
        if 'api' in keyword_lower:
            return f"Complete Guide to {keyword.title()}: API Integration Tutorial"
        elif 'tool' in keyword_lower:
            return f"Best {keyword.title()} Tools: Complete Comparison Guide"
        elif 'guide' in keyword_lower or 'tutorial' in keyword_lower:
            return f"How to {keyword.title()}: Step-by-Step Guide"
        elif 'seo' in keyword_lower:
            return f"{keyword.title()}: SEO Best Practices and Implementation"
        elif 'analysis' in keyword_lower:
            return f"{keyword.title()}: Complete Analysis and Implementation Guide"
        else:
            return f"Ultimate Guide to {keyword.title()}: Everything You Need to Know"
    
    def _suggest_tools_from_keywords(self, keywords: List[Dict[str, Any]]) -> List[str]:
        """Suggest specific tools based on keyword analysis"""
        suggestions = []
        
        # Look for tool-related patterns
        tool_patterns = {
            'calculator': ['calculator', 'calc', 'compute'],
            'checker': ['checker', 'check', 'verify'],
            'analyzer': ['analyzer', 'analysis', 'audit'],
            'generator': ['generator', 'generate', 'create'],
            'converter': ['converter', 'convert', 'transform']
        }
        
        for pattern, words in tool_patterns.items():
            matching_keywords = [kw for kw in keywords if any(word in kw.get('keyword', '').lower() for word in words)]
            if matching_keywords:
                # Generate tool suggestion based on the theme
                theme = self._extract_theme_from_keywords(matching_keywords)
                suggestions.append(f"{theme} {pattern.title()}")
        
        return suggestions[:5]  # Top 5 suggestions
    
    def _extract_theme_from_keywords(self, keywords: List[Dict[str, Any]]) -> str:
        """Extract theme from keywords for tool naming"""
        all_keywords = ' '.join([kw.get('keyword', '') for kw in keywords]).lower()
        
        if 'seo' in all_keywords:
            return 'SEO'
        elif 'api' in all_keywords:
            return 'API'
        elif 'marketing' in all_keywords:
            return 'Marketing'
        elif 'data' in all_keywords:
            return 'Data'
        else:
            return 'Web'
    
    def _suggest_outreach_targets(self, backlinks: List[Dict[str, Any]]) -> List[str]:
        """Suggest outreach targets based on existing backlinks"""
        targets = []
        
        # Analyze high-quality backlink sources
        high_dr_sources = [bl for bl in backlinks if bl.get('domain_rank', 0) > 40]
        
        for bl in high_dr_sources[:10]:
            domain = bl.get('domain', '')
            if domain and domain not in targets:
                targets.append(f"{domain} - Potential guest posting opportunity")
        
        return targets[:5]  # Top 5 targets
    
    def _get_keyword_content_suggestion(self, keyword: str) -> str:
        """Get specific content suggestion based on keyword"""
        keyword_lower = keyword.lower()
        
        if 'api' in keyword_lower:
            return "Create API documentation, tutorials, or integration guides"
        elif 'tool' in keyword_lower:
            return "Build a free tool or calculator related to this topic"
        elif 'calculator' in keyword_lower:
            return "Develop an interactive calculator for this use case"
        elif 'checker' in keyword_lower:
            return "Create a free checker tool for this functionality"
        elif 'guide' in keyword_lower or 'tutorial' in keyword_lower:
            return "Create comprehensive step-by-step guides"
        elif 'seo' in keyword_lower:
            return "Develop SEO-focused content and tools"
        elif 'analysis' in keyword_lower:
            return "Create analytical reports and data visualization tools"
        elif 'audit' in keyword_lower:
            return "Build an automated audit tool"
        elif 'generator' in keyword_lower:
            return "Create a free generator tool"
        elif 'converter' in keyword_lower:
            return "Build a conversion tool"
        else:
            return "Create comprehensive content around this topic"
    
    def _get_backlink_partnership_suggestion(self, domain: str, anchor_text: str) -> str:
        """Get specific partnership suggestion based on backlink source"""
        domain_lower = domain.lower()
        anchor_lower = anchor_text.lower()
        
        if 'blog' in domain_lower or 'news' in domain_lower:
            return "Guest posting opportunity"
        elif 'tool' in domain_lower or 'software' in domain_lower:
            return "Tool integration or partnership opportunity"
        elif 'seo' in domain_lower or 'marketing' in domain_lower:
            return "Industry collaboration opportunity"
        elif 'developer' in domain_lower or 'tech' in domain_lower:
            return "Developer community engagement"
        elif 'forum' in domain_lower or 'community' in domain_lower:
            return "Community participation and content sharing"
        elif 'directory' in domain_lower:
            return "Directory listing and resource page opportunities"
        else:
            return "Potential collaboration opportunity"
    
    def _get_default_development_plan(self) -> Dict[str, Any]:
        """Return a default development plan if LLM generation fails"""
        return {
            "title": "Comprehensive Domain Development Plan",
            "description": "Data-driven strategies to increase organic traffic and improve domain authority through content optimization, technical SEO, and link building",
            "strategies": [
                {
                    "id": "content_optimization",
                    "title": "Content Optimization & Expansion Strategy",
                    "description": "Audit and optimize existing content while creating new high-value content targeting specific keywords",
                    "priority": "high",
                    "estimated_effort": "medium",
                    "expected_impact": "high",
                    "timeline": "4-6 weeks",
                    "steps": [
                        "Conduct comprehensive content audit using tools like Screaming Frog",
                        "Identify top-performing content and optimize for better rankings",
                        "Create 10-15 new high-quality blog posts targeting long-tail keywords",
                        "Optimize meta titles and descriptions for all pages",
                        "Implement schema markup for better search visibility",
                        "Create topic clusters around main keyword themes"
                    ],
                    "keywords": ["long-tail keywords", "LSI keywords", "semantic keywords"],
                    "expected_traffic_increase": "25-40% increase in 3-4 months"
                },
                {
                    "id": "technical_seo",
                    "title": "Technical SEO Optimization",
                    "description": "Improve site speed, mobile experience, and technical foundation for better search rankings",
                    "priority": "high",
                    "estimated_effort": "medium",
                    "expected_impact": "high",
                    "timeline": "2-3 weeks",
                    "steps": [
                        "Optimize Core Web Vitals (LCP, FID, CLS)",
                        "Implement proper heading structure (H1, H2, H3)",
                        "Fix any crawl errors and broken links",
                        "Optimize images with proper alt tags and compression",
                        "Implement XML sitemaps and robots.txt optimization",
                        "Ensure mobile-first indexing compliance"
                    ],
                    "keywords": ["technical SEO", "site speed", "mobile optimization"],
                    "expected_traffic_increase": "15-25% increase in 2-3 months"
                },
                {
                    "id": "link_building",
                    "title": "Strategic Link Building Campaign",
                    "description": "Build high-quality backlinks through outreach, content marketing, and relationship building",
                    "priority": "medium",
                    "estimated_effort": "high",
                    "expected_impact": "high",
                    "timeline": "3-4 months",
                    "steps": [
                        "Identify 50+ high-authority websites in your niche",
                        "Create linkable assets (infographics, guides, tools)",
                        "Conduct guest posting on relevant industry blogs",
                        "Build relationships with industry influencers",
                        "Submit to relevant directories and resource pages",
                        "Monitor and disavow toxic backlinks"
                    ],
                    "keywords": ["link building", "backlink acquisition", "domain authority"],
                    "expected_traffic_increase": "30-50% increase in 4-6 months"
                }
            ],
            "timeline": [
                {
                    "phase": "Phase 1: Foundation (Weeks 1-4)",
                    "duration": "4 weeks",
                    "focus": "Technical SEO improvements and content audit"
                },
                {
                    "phase": "Phase 2: Content Creation (Weeks 5-8)",
                    "duration": "4 weeks",
                    "focus": "Content optimization and new content creation"
                },
                {
                    "phase": "Phase 3: Link Building (Weeks 9-16)",
                    "duration": "8 weeks",
                    "focus": "Strategic link building and relationship building"
                }
            ],
            "success_metrics": [
                "Organic traffic increase by 40-60% within 6 months",
                "Domain Rating improvement by 10-15 points",
                "Average keyword ranking improvement by 5-10 positions",
                "Core Web Vitals scores in 'Good' range",
                "50+ new high-quality backlinks acquired"
            ]
        }
