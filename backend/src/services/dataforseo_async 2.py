"""
DataForSEO Async Service - Implements standard POST → GET pattern for cost efficiency
"""

import asyncio
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import structlog

from utils.config import get_settings
from services.secrets_service import get_secrets_service
from services.database import get_database
from models.domain_analysis import DetailedAnalysisData, AsyncTask, AsyncTaskStatus, DetailedDataType

logger = structlog.get_logger()


class DataForSEOAsyncService:
    """Service for DataForSEO async operations using standard POST → GET pattern"""
    
    def __init__(self):
        self.settings = get_settings()
        self.secrets_service = get_secrets_service()
        self.timeout = 30.0
        self.poll_interval = 2  # seconds
        self.max_poll_attempts = 30  # 1 minute max
        self._credentials = None
        self.cost_tracker = {
            "api_calls": 0,
            "estimated_cost": 0.0,
            "cost_per_call": 0.01  # Estimated cost per API call
        }
    
    async def _get_credentials(self) -> Optional[Dict[str, str]]:
        """Get DataForSEO credentials"""
        if self._credentials is None:
            self._credentials = await self.secrets_service.get_dataforseo_credentials()
        return self._credentials
    
    async def get_detailed_backlinks_async(self, domain: str, limit: int = 10000) -> Optional[Dict[str, Any]]:
        """Get detailed backlinks using async pattern"""
        return await self._execute_async_task(
            domain=domain,
            task_type=DetailedDataType.BACKLINKS,
            post_endpoint="/backlinks/backlinks/task_post",
            get_endpoint="/backlinks/backlinks/task_get",
            post_data={
                "target": domain,
                "limit": limit,
                "mode": "as_is",
                "filters": ["dofollow", "=", True]
            }
        )
    
    async def get_detailed_keywords_async(self, domain: str, limit: int = 10000) -> Optional[Dict[str, Any]]:
        """Get detailed keywords using async pattern"""
        return await self._execute_async_task(
            domain=domain,
            task_type=DetailedDataType.KEYWORDS,
            post_endpoint="/dataforseo_labs/google/ranked_keywords/task_post",
            get_endpoint="/dataforseo_labs/google/ranked_keywords/task_get",
            post_data={
                "target": domain,
                "language_name": "English",
                "location_name": "United States",
                "load_rank_absolute": True,
                "limit": limit
            }
        )
    
    async def get_referring_domains_async(self, domain: str, limit: int = 10000) -> Optional[Dict[str, Any]]:
        """Get referring domains using async pattern"""
        return await self._execute_async_task(
            domain=domain,
            task_type=DetailedDataType.REFERRING_DOMAINS,
            post_endpoint="/backlinks/backlinks/task_post",
            get_endpoint="/backlinks/backlinks/task_get",
            post_data={
                "target": domain,
                "limit": limit,
                "mode": "as_is",
                "filters": ["dofollow", "=", True],
                "order_by": ["domain_from_rank,desc"]
            }
        )
    
    async def _execute_async_task(self, domain: str, task_type: DetailedDataType, 
                                 post_endpoint: str, get_endpoint: str, 
                                 post_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute async task pattern: POST → poll → GET"""
        try:
            # Check if data already exists and is fresh
            db = get_database()
            existing_data = await db.get_detailed_data(domain, task_type)
            if existing_data and self._is_data_fresh(existing_data):
                logger.info("Using fresh cached data", domain=domain, task_type=task_type)
                return existing_data.json_data
            
            # Check for existing pending task
            existing_task = await db.get_pending_task(domain, task_type)
            if existing_task:
                logger.info("Found existing pending task", domain=domain, task_type=task_type, task_id=existing_task.task_id)
                return await self._wait_for_task_completion(domain, task_type, existing_task.task_id)
            
            # Step 1: POST task
            task_id = await self._post_task(post_endpoint, post_data)
            if not task_id:
                return None
            
            # Save task to database
            await db.save_async_task(AsyncTask(
                domain_name=domain,
                task_id=task_id,
                task_type=task_type,
                status=AsyncTaskStatus.PROCESSING
            ))
            
            # Step 2: Poll for completion (pass get_endpoint for correct API call)
            return await self._wait_for_task_completion(domain, task_type, task_id, get_endpoint)
            
        except Exception as e:
            logger.error("Async task execution failed", domain=domain, task_type=task_type, error=str(e))
            return None
    
    async def _post_task(self, endpoint: str, post_data: Dict[str, Any]) -> Optional[str]:
        """POST task to DataForSEO"""
        try:
            credentials = await self._get_credentials()
            if not credentials:
                return None
            
            # DataForSEO expects an array of tasks
            tasks_array = [post_data]
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{credentials['api_url']}{endpoint}",
                    auth=(credentials['login'], credentials['password']),
                    json=tasks_array
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status_code") == 20000 and data.get("tasks"):
                        task_id = data["tasks"][0].get("id")
                        logger.info("Task posted successfully", task_id=task_id, endpoint=endpoint)
                        return task_id
                
                logger.error("Task post failed", status=response.status_code, response=data)
                return None
                
        except Exception as e:
            logger.error("Task post exception", endpoint=endpoint, error=str(e))
            return None
    
    async def _wait_for_task_completion(self, domain: str, task_type: DetailedDataType, task_id: str, get_endpoint: str = None) -> Optional[Dict[str, Any]]:
        """Poll for task completion and retrieve results"""
        try:
            credentials = await self._get_credentials()
            if not credentials:
                return None
            
            db = get_database()
            
            # Get human-readable task type for status messages
            task_type_messages = {
                DetailedDataType.BACKLINKS: "backlinks results",
                DetailedDataType.KEYWORDS: "keywords results", 
                DetailedDataType.REFERRING_DOMAINS: "referring domains results"
            }
            task_message = task_type_messages.get(task_type, "results")
            
            for attempt in range(self.max_poll_attempts):
                logger.info(f"Polling for {task_message}", domain=domain, attempt=attempt + 1, max_attempts=self.max_poll_attempts)
                await asyncio.sleep(self.poll_interval)
                
                # Check if task is ready
                if await self._is_task_ready(credentials, task_id, task_type):
                    logger.info(f"Task completed, retrieving {task_message}", domain=domain, task_id=task_id)
                    # Get results with correct endpoint
                    results = await self._get_task_results(credentials, task_id, task_type, get_endpoint)
                    if results:
                        # Validate and filter results before saving
                        validated_results = self._validate_and_filter_results(results, domain, task_type)
                        if validated_results:
                            # Save results to database
                            detailed_data = DetailedAnalysisData(
                                domain_name=domain,
                                data_type=task_type,
                                json_data=validated_results,
                                task_id=task_id
                            )
                            await db.save_detailed_data(detailed_data)
                            
                            # Update task status
                            await db.update_async_task_status(task_id, AsyncTaskStatus.COMPLETED)
                            
                            logger.info("Task completed successfully", domain=domain, task_type=task_type, task_id=task_id)
                            return validated_results
                        else:
                            logger.warning("Task results failed validation - no valid data to save", domain=domain, task_type=task_type, task_id=task_id)
                            await db.update_async_task_status(task_id, AsyncTaskStatus.FAILED, "Results failed validation - no valid data")
                            return None
                
                logger.debug("Task still processing", domain=domain, task_type=task_type, attempt=attempt + 1)
            
            # Task timed out
            await db.update_async_task_status(task_id, AsyncTaskStatus.FAILED, "Task timed out")
            logger.error("Task timed out", domain=domain, task_type=task_type, task_id=task_id)
            return None
            
        except Exception as e:
            logger.error("Task completion wait failed", domain=domain, task_type=task_type, error=str(e))
            return None
    
    async def _is_task_ready(self, credentials: Dict[str, str], task_id: str, task_type: DetailedDataType) -> bool:
        """Check if task is ready for results retrieval"""
        try:
            # Use correct endpoint based on task type
            if task_type == DetailedDataType.KEYWORDS:
                ready_endpoint = "/dataforseo_labs/google/ranked_keywords/tasks_ready"
            elif task_type == DetailedDataType.REFERRING_DOMAINS:
                ready_endpoint = "/backlinks/backlinks/tasks_ready"
            else:  # BACKLINKS
                ready_endpoint = "/backlinks/backlinks/tasks_ready"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{credentials['api_url']}{ready_endpoint}",
                    auth=(credentials['login'], credentials['password'])
                )
                
                if response.status_code == 200:
                    data = response.json()
                    ready_tasks = data.get("tasks", [])
                    return any(task.get("id") == task_id for task in ready_tasks)
                
                return False
                
        except Exception as e:
            logger.error("Task ready check failed", task_id=task_id, error=str(e))
            return False
    
    async def _get_task_results(self, credentials: Dict[str, str], task_id: str, task_type: DetailedDataType, get_endpoint: str = None) -> Optional[Dict[str, Any]]:
        """Get task results using the correct endpoint"""
        try:
            # Use provided endpoint or determine from task type
            if get_endpoint:
                endpoint = get_endpoint
            elif task_type == DetailedDataType.KEYWORDS:
                endpoint = "/dataforseo_labs/google/ranked_keywords/task_get"
            elif task_type == DetailedDataType.REFERRING_DOMAINS:
                endpoint = "/backlinks/backlinks/task_get"
            else:  # BACKLINKS
                endpoint = "/backlinks/backlinks/task_get"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{credentials['api_url']}{endpoint}/{task_id}",
                    auth=(credentials['login'], credentials['password'])
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status_code") == 20000 and data.get("tasks"):
                        return data["tasks"][0].get("result", [{}])[0]
                
                return None
                
        except Exception as e:
            logger.error("Get task results failed", task_id=task_id, task_type=task_type.value, error=str(e))
            return None
    
    def _validate_and_filter_results(self, results: Dict[str, Any], domain: str, task_type: DetailedDataType) -> Optional[Dict[str, Any]]:
        """Validate and filter results to remove sample/test data"""
        try:
            if not results:
                return None
            
            # For keywords, validate that they're actually related to the domain
            if task_type == DetailedDataType.KEYWORDS:
                items = results.get("items", [])
                if not items:
                    logger.warning("Keywords results have no items", domain=domain)
                    return None
                
                # Filter out sample/test keywords
                # Sample keywords often point to dataforseo.com or other test domains
                valid_items = []
                domain_lower = domain.lower().replace('www.', '')
                
                for item in items:
                    # Get the URL from the keyword result
                    serp_item = item.get("ranked_serp_element", {}).get("serp_item", {})
                    url = serp_item.get("url", "")
                    keyword_text = item.get("keyword_data", {}).get("keyword", "")
                    
                    # Skip if URL is empty or points to test/sample domains
                    if not url:
                        continue
                    
                    url_lower = url.lower()
                    
                    # Filter out sample/test data
                    # Sample keywords often point to dataforseo.com, example.com, or test domains
                    if any(test_domain in url_lower for test_domain in [
                        'dataforseo.com',
                        'example.com',
                        'test.com',
                        'sample.com',
                        'demo.com'
                    ]):
                        logger.debug("Filtered out sample keyword", domain=domain, keyword=keyword_text, url=url)
                        continue
                    
                    # Validate that the URL is related to the target domain
                    # The URL should contain the domain name (or be from the domain)
                    if domain_lower not in url_lower:
                        # This might be a keyword ranking for a different domain
                        # For now, we'll keep it but log a warning
                        logger.debug("Keyword URL doesn't match domain", domain=domain, keyword=keyword_text, url=url)
                    
                    valid_items.append(item)
                
                if not valid_items:
                    logger.warning("No valid keywords found after filtering", domain=domain, original_count=len(items))
                    return None
                
                # Update results with filtered items and correct total_count
                results["items"] = valid_items
                results["total_count"] = len(valid_items)
                results["items_count"] = len(valid_items)
                
                logger.info("Keywords validated and filtered", 
                           domain=domain, 
                           original_count=len(items), 
                           valid_count=len(valid_items))
                
                return results
            
            # For other data types, return as-is (add validation if needed)
            return results
            
        except Exception as e:
            logger.error("Results validation failed", domain=domain, task_type=task_type.value, error=str(e))
            return None
    
    def _is_data_fresh(self, data: DetailedAnalysisData, max_age_hours: int = 24) -> bool:
        """Check if data is fresh enough to use"""
        if not data.created_at:
            return False
        
        age = datetime.utcnow() - data.created_at
        return age.total_seconds() < (max_age_hours * 3600)
    
    async def health_check(self) -> bool:
        """Check if DataForSEO async service is healthy"""
        try:
            credentials = await self._get_credentials()
            if not credentials:
                return False
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{credentials['api_url']}/ping",
                    auth=(credentials['login'], credentials['password'])
                )
                return response.status_code == 200
        except Exception as e:
            logger.error("DataForSEO async health check failed", error=str(e))
            return False
    
    def _track_api_call(self, cost: float = None):
        """Track API call for cost monitoring"""
        self.cost_tracker["api_calls"] += 1
        if cost is not None:
            self.cost_tracker["estimated_cost"] += cost
        else:
            self.cost_tracker["estimated_cost"] += self.cost_tracker["cost_per_call"]
        
        logger.info("API call tracked", 
                   total_calls=self.cost_tracker["api_calls"],
                   estimated_cost=self.cost_tracker["estimated_cost"])
    
    def get_cost_metrics(self) -> Dict[str, Any]:
        """Get current cost metrics"""
        return {
            "total_api_calls": self.cost_tracker["api_calls"],
            "estimated_total_cost": round(self.cost_tracker["estimated_cost"], 4),
            "average_cost_per_call": round(
                self.cost_tracker["estimated_cost"] / max(1, self.cost_tracker["api_calls"]), 4
            ),
            "cost_savings_vs_live": round(
                self.cost_tracker["estimated_cost"] * 0.7, 4  # 70% savings with async
            )
        }
    
    def reset_cost_tracker(self):
        """Reset cost tracking metrics"""
        self.cost_tracker = {
            "api_calls": 0,
            "estimated_cost": 0.0,
            "cost_per_call": 0.01
        }
