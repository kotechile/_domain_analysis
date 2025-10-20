"""
External API services for domain analysis
"""

import httpx
import asyncio
from typing import Dict, Any, Optional, List
import structlog
from datetime import datetime

from utils.config import get_settings
from models.domain_analysis import DataForSEOMetrics, DataSource
from services.database import get_database

logger = structlog.get_logger()


class DataForSEOService:
    """Service for DataForSEO API integration"""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.DATAFORSEO_API_URL
        self.auth = (self.settings.DATAFORSEO_LOGIN, self.settings.DATAFORSEO_PASSWORD)
        self.timeout = 30.0
    
    async def health_check(self) -> bool:
        """Check if DataForSEO API is accessible"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/ping",
                    auth=self.auth
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning("DataForSEO health check failed", error=str(e))
            return False
    
    async def get_domain_analytics(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get domain analytics data from DataForSEO"""
        try:
            # Check cache first
            db = get_database()
            cached_data = await db.get_raw_data(domain, DataSource.DATAFORSEO)
            if cached_data:
                logger.info("Using cached DataForSEO data", domain=domain)
                return cached_data
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Get domain analytics
                analytics_response = await client.post(
                    f"{self.base_url}/dataforseo_labs/google/domain_analytics/live",
                    auth=self.auth,
                    json=[{
                        "target": domain,
                        "language_code": "en",
                        "location_code": 2840,  # United States
                        "limit": 1
                    }]
                )
                
                if analytics_response.status_code != 200:
                    logger.error("DataForSEO analytics request failed", 
                               domain=domain, status=analytics_response.status_code)
                    return None
                
                analytics_data = analytics_response.json()
                
                # Get backlinks data
                backlinks_response = await client.post(
                    f"{self.base_url}/dataforseo_labs/google/backlinks/live",
                    auth=self.auth,
                    json=[{
                        "target": domain,
                        "limit": 100,
                        "order_by": ["domain_rank,desc"]
                    }]
                )
                
                if backlinks_response.status_code != 200:
                    logger.warning("DataForSEO backlinks request failed", 
                                 domain=domain, status=backlinks_response.status_code)
                    backlinks_data = {"items": []}
                else:
                    backlinks_data = backlinks_response.json()
                
                # Get keywords data
                keywords_response = await client.post(
                    f"{self.base_url}/dataforseo_labs/google/ranked_keywords/live",
                    auth=self.auth,
                    json=[{
                        "target": domain,
                        "language_code": "en",
                        "location_code": 2840,
                        "limit": 1000
                    }]
                )
                
                if keywords_response.status_code != 200:
                    logger.warning("DataForSEO keywords request failed", 
                                 domain=domain, status=keywords_response.status_code)
                    keywords_data = {"items": []}
                else:
                    keywords_data = keywords_response.json()
                
                # Combine all data
                combined_data = {
                    "analytics": analytics_data.get("tasks", [{}])[0].get("result", [{}])[0] if analytics_data.get("tasks") else {},
                    "backlinks": backlinks_data.get("tasks", [{}])[0].get("result", [{}])[0] if backlinks_data.get("tasks") else {},
                    "keywords": keywords_data.get("tasks", [{}])[0].get("result", [{}])[0] if keywords_data.get("tasks") else {},
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Cache the data
                await db.save_raw_data(domain, DataSource.DATAFORSEO, combined_data)
                
                logger.info("DataForSEO data retrieved successfully", domain=domain)
                return combined_data
                
        except Exception as e:
            logger.error("Failed to get DataForSEO data", domain=domain, error=str(e))
            return None
    
    def parse_domain_metrics(self, data: Dict[str, Any]) -> DataForSEOMetrics:
        """Parse DataForSEO data into domain metrics"""
        try:
            analytics = data.get("analytics", {})
            backlinks = data.get("backlinks", {})
            keywords = data.get("keywords", {})
            
            # Extract referring domains info
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
            
            # Extract keywords info
            organic_keywords = []
            if keywords.get("items"):
                for item in keywords["items"][:1000]:  # Top 1000
                    organic_keywords.append({
                        "keyword": item.get("keyword", ""),
                        "rank": item.get("rank_group", 0),
                        "search_volume": item.get("search_volume", 0),
                        "traffic_share": item.get("traffic_share", 0.0),
                        "cpc": item.get("cpc", 0.0),
                        "competition": item.get("competition", 0.0)
                    })
            
            return DataForSEOMetrics(
                domain_rating_dr=analytics.get("domain_rank", 0),
                organic_traffic_est=analytics.get("organic_traffic", 0),
                total_referring_domains=backlinks.get("total_count", 0),
                total_backlinks=backlinks.get("backlinks_count", 0),
                referring_domains_info=referring_domains_info,
                organic_keywords=organic_keywords
            )
            
        except Exception as e:
            logger.error("Failed to parse DataForSEO metrics", error=str(e))
            return DataForSEOMetrics()


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
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.base_url,
                    params={
                        "url": domain,
                        "output": "json",
                        "limit": 10000,
                        "collapse": "timestamp:8"  # Group by day
                    }
                )
                
                if response.status_code != 200:
                    logger.error("Wayback Machine request failed", 
                               domain=domain, status=response.status_code)
                    return None
                
                data = response.json()
                
                if not data or len(data) < 2:  # Header + data
                    logger.warning("No Wayback Machine data found", domain=domain)
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
                
        except Exception as e:
            logger.error("Failed to get Wayback Machine data", domain=domain, error=str(e))
            return None


class LLMService:
    """Service for LLM integration (Gemini API)"""
    
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.GEMINI_API_KEY
        self.timeout = 60.0
    
    async def health_check(self) -> bool:
        """Check if LLM service is accessible"""
        try:
            # Simple test request
            test_prompt = "Test connection"
            result = await self.generate_analysis(test_prompt, {})
            return result is not None
        except Exception as e:
            logger.warning("LLM service health check failed", error=str(e))
            return False
    
    async def generate_analysis(self, domain: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate domain analysis using LLM"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel('gemini-pro')
            
            # Prepare the analysis prompt
            prompt = self._build_analysis_prompt(domain, data)
            
            response = await asyncio.to_thread(
                model.generate_content,
                prompt
            )
            
            # Parse the response (assuming JSON format)
            analysis_text = response.text
            
            # Try to extract JSON from the response
            import json
            import re
            
            # Look for JSON in the response
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                analysis_data = json.loads(json_match.group())
            else:
                # Fallback: create structured response from text
                analysis_data = self._parse_text_response(analysis_text)
            
            logger.info("LLM analysis generated successfully", domain=domain)
            return analysis_data
            
        except Exception as e:
            logger.error("Failed to generate LLM analysis", domain=domain, error=str(e))
            return None
    
    def _build_analysis_prompt(self, domain: str, data: Dict[str, Any]) -> str:
        """Build the analysis prompt for the LLM"""
        analytics = data.get("analytics", {})
        backlinks = data.get("backlinks", {})
        keywords = data.get("keywords", {})
        wayback = data.get("wayback", {})
        
        prompt = f"""
        Analyze the following domain data for {domain} and provide a comprehensive SEO analysis report.
        
        Domain Analytics:
        - Domain Rating (DR): {analytics.get('domain_rank', 'N/A')}
        - Organic Traffic: {analytics.get('organic_traffic', 'N/A')}
        - Total Referring Domains: {backlinks.get('total_count', 'N/A')}
        - Total Backlinks: {backlinks.get('backlinks_count', 'N/A')}
        
        Top Keywords (showing first 10):
        {self._format_keywords(keywords.get('items', [])[:10])}
        
        Top Referring Domains (showing first 10):
        {self._format_backlinks(backlinks.get('items', [])[:10])}
        
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
