# Domain Analysis Workflow Improvement - Implementation Plan

## Executive Summary

This plan outlines the implementation of critical improvements to the domain analysis workflow to address cost optimization, data completeness, and AI analysis quality. The changes will reduce DataForSEO API costs by 60-80% while ensuring comprehensive AI analysis with detailed backlink quality assessment.

## Current State Analysis

### Issues Identified
1. **Incomplete AI Analysis**: Optional detailed data collection leads to incomplete analysis
2. **High API Costs**: Using expensive "Live" endpoints for all DataForSEO queries
3. **Data Re-querying**: No persistence of detailed data, leading to repeated expensive API calls
4. **Limited Scalability**: Synchronous API calls limit bulk analysis capabilities

### Current API Usage (Cost Analysis)
- **Backlinks Summary**: `/backlinks/summary/live` - High cost, immediate results
- **Detailed Backlinks**: `/backlinks/backlinks/live` - Very high cost, immediate results
- **Keywords**: `/dataforseo_labs/google/ranked_keywords/live` - High cost, immediate results
- **Referring Domains**: `/backlinks/backlinks/live` with aggregation - Very high cost

## Implementation Phases

### Phase 1: Database Schema Enhancement (Week 1)

#### 1.1 Create Detailed Data Storage Tables
**File**: `backend/supabase_migrations/003_create_detailed_data_tables.sql`

```sql
-- Create detailed analysis data table
CREATE TABLE IF NOT EXISTS detailed_analysis_data (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_name VARCHAR(255) NOT NULL,
    data_type VARCHAR(50) NOT NULL, -- 'backlinks', 'keywords', 'referring_domains'
    json_data JSONB NOT NULL,
    task_id VARCHAR(255), -- DataForSEO task ID for reference
    data_source VARCHAR(50) DEFAULT 'dataforseo',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(domain_name, data_type)
);

-- Create async task tracking table
CREATE TABLE IF NOT EXISTS async_tasks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_name VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL UNIQUE,
    task_type VARCHAR(50) NOT NULL, -- 'backlinks', 'keywords', 'referring_domains'
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

-- Update reports table
ALTER TABLE reports ADD COLUMN detailed_data_available JSONB DEFAULT '{}';
ALTER TABLE reports ADD COLUMN analysis_phase VARCHAR(50) DEFAULT 'essential'; -- 'essential', 'detailed', 'ai_analysis', 'completed'

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_detailed_data_domain_type ON detailed_analysis_data(domain_name, data_type);
CREATE INDEX IF NOT EXISTS idx_detailed_data_expires_at ON detailed_analysis_data(expires_at);
CREATE INDEX IF NOT EXISTS idx_async_tasks_domain_type ON async_tasks(domain_name, task_type);
CREATE INDEX IF NOT EXISTS idx_async_tasks_status ON async_tasks(status);
CREATE INDEX IF NOT EXISTS idx_async_tasks_task_id ON async_tasks(task_id);

-- Enable RLS
ALTER TABLE detailed_analysis_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE async_tasks ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Public can read detailed data" ON detailed_analysis_data FOR SELECT USING (true);
CREATE POLICY "Service role can manage detailed data" ON detailed_analysis_data FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage async tasks" ON async_tasks FOR ALL USING (auth.role() = 'service_role');
```

#### 1.2 Update Data Models
**File**: `backend/src/models/domain_analysis.py`

```python
# Add new models
class DetailedDataType(str, Enum):
    BACKLINKS = "backlinks"
    KEYWORDS = "keywords"
    REFERRING_DOMAINS = "referring_domains"

class AsyncTaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DetailedAnalysisData(BaseModel):
    id: Optional[str] = None
    domain_name: str
    data_type: DetailedDataType
    json_data: Dict[str, Any]
    task_id: Optional[str] = None
    data_source: str = "dataforseo"
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

class AsyncTask(BaseModel):
    id: Optional[str] = None
    domain_name: str
    task_id: str
    task_type: DetailedDataType
    status: AsyncTaskStatus = AsyncTaskStatus.PENDING
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0

# Update existing models
class DomainAnalysisReport(BaseModel):
    # ... existing fields ...
    detailed_data_available: Dict[str, bool] = {}
    analysis_phase: str = "essential"
```

### Phase 2: DataForSEO Async Pattern Implementation (Week 2)

#### 2.1 Create Async DataForSEO Service
**File**: `backend/src/services/dataforseo_async.py`

```python
"""
DataForSEO Async Service - Implements standard POST → GET pattern
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
        self.max_poll_attempts = 30  # 1 minute max wait
        self._credentials = None
    
    async def _get_credentials(self) -> Optional[Dict[str, str]]:
        """Get DataForSEO credentials"""
        if self._credentials is None:
            self._credentials = await self.secrets_service.get_dataforseo_credentials()
        return self._credentials
    
    async def get_detailed_backlinks_async(self, domain: str, limit: int = 1000) -> Optional[Dict[str, Any]]:
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
    
    async def get_detailed_keywords_async(self, domain: str, limit: int = 1000) -> Optional[Dict[str, Any]]:
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
    
    async def get_referring_domains_async(self, domain: str, limit: int = 800) -> Optional[Dict[str, Any]]:
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
            
            # Step 2: Poll for completion
            return await self._wait_for_task_completion(domain, task_type, task_id)
            
        except Exception as e:
            logger.error("Async task execution failed", domain=domain, task_type=task_type, error=str(e))
            return None
    
    async def _post_task(self, endpoint: str, post_data: Dict[str, Any]) -> Optional[str]:
        """POST task to DataForSEO"""
        try:
            credentials = await self._get_credentials()
            if not credentials:
                return None
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{credentials['api_url']}{endpoint}",
                    auth=(credentials['login'], credentials['password']),
                    json=post_data
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
    
    async def _wait_for_task_completion(self, domain: str, task_type: DetailedDataType, task_id: str) -> Optional[Dict[str, Any]]:
        """Poll for task completion and retrieve results"""
        try:
            credentials = await self._get_credentials()
            if not credentials:
                return None
            
            db = get_database()
            
            for attempt in range(self.max_poll_attempts):
                await asyncio.sleep(self.poll_interval)
                
                # Check if task is ready
                if await self._is_task_ready(credentials, task_id):
                    # Get results
                    results = await self._get_task_results(credentials, task_id)
                    if results:
                        # Save results to database
                        detailed_data = DetailedAnalysisData(
                            domain_name=domain,
                            data_type=task_type,
                            json_data=results,
                            task_id=task_id
                        )
                        await db.save_detailed_data(detailed_data)
                        
                        # Update task status
                        await db.update_async_task_status(task_id, AsyncTaskStatus.COMPLETED)
                        
                        logger.info("Task completed successfully", domain=domain, task_type=task_type, task_id=task_id)
                        return results
                
                logger.debug("Task still processing", domain=domain, task_type=task_type, attempt=attempt + 1)
            
            # Task timed out
            await db.update_async_task_status(task_id, AsyncTaskStatus.FAILED, "Task timed out")
            logger.error("Task timed out", domain=domain, task_type=task_type, task_id=task_id)
            return None
            
        except Exception as e:
            logger.error("Task completion wait failed", domain=domain, task_type=task_type, error=str(e))
            return None
    
    async def _is_task_ready(self, credentials: Dict[str, str], task_id: str) -> bool:
        """Check if task is ready for results retrieval"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{credentials['api_url']}/backlinks/backlinks/tasks_ready",
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
    
    async def _get_task_results(self, credentials: Dict[str, str], task_id: str) -> Optional[Dict[str, Any]]:
        """Get task results"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{credentials['api_url']}/backlinks/backlinks/task_get/{task_id}",
                    auth=(credentials['login'], credentials['password'])
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status_code") == 20000 and data.get("tasks"):
                        return data["tasks"][0].get("result", [{}])[0]
                
                return None
                
        except Exception as e:
            logger.error("Get task results failed", task_id=task_id, error=str(e))
            return None
    
    def _is_data_fresh(self, data: DetailedAnalysisData, max_age_hours: int = 24) -> bool:
        """Check if data is fresh enough to use"""
        if not data.created_at:
            return False
        
        age = datetime.utcnow() - data.created_at
        return age.total_seconds() < (max_age_hours * 3600)
```

#### 2.2 Update Database Service
**File**: `backend/src/services/database.py`

```python
# Add new methods to DatabaseService class

async def get_detailed_data(self, domain: str, data_type: DetailedDataType) -> Optional[DetailedAnalysisData]:
    """Get detailed analysis data for a domain and type"""
    try:
        result = self.client.table('detailed_analysis_data').select('*').eq('domain_name', domain).eq('data_type', data_type.value).execute()
        
        if result.data:
            data = result.data[0]
            return DetailedAnalysisData(
                id=data['id'],
                domain_name=data['domain_name'],
                data_type=DetailedDataType(data['data_type']),
                json_data=data['json_data'],
                task_id=data.get('task_id'),
                data_source=data.get('data_source', 'dataforseo'),
                created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')),
                expires_at=datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00')) if data.get('expires_at') else None
            )
        return None
        
    except Exception as e:
        logger.error("Failed to get detailed data", domain=domain, data_type=data_type, error=str(e))
        return None

async def save_detailed_data(self, data: DetailedAnalysisData) -> str:
    """Save detailed analysis data"""
    try:
        data_dict = {
            'domain_name': data.domain_name,
            'data_type': data.data_type.value,
            'json_data': data.json_data,
            'task_id': data.task_id,
            'data_source': data.data_source,
            'expires_at': data.expires_at.isoformat() if data.expires_at else None
        }
        
        result = self.client.table('detailed_analysis_data').upsert(data_dict).execute()
        return result.data[0]['id'] if result.data else None
        
    except Exception as e:
        logger.error("Failed to save detailed data", domain=data.domain_name, data_type=data.data_type, error=str(e))
        return None

async def get_pending_task(self, domain: str, task_type: DetailedDataType) -> Optional[AsyncTask]:
    """Get pending async task for domain and type"""
    try:
        result = self.client.table('async_tasks').select('*').eq('domain_name', domain).eq('task_type', task_type.value).in_('status', ['pending', 'processing']).execute()
        
        if result.data:
            task_data = result.data[0]
            return AsyncTask(
                id=task_data['id'],
                domain_name=task_data['domain_name'],
                task_id=task_data['task_id'],
                task_type=DetailedDataType(task_data['task_type']),
                status=AsyncTaskStatus(task_data['status']),
                created_at=datetime.fromisoformat(task_data['created_at'].replace('Z', '+00:00')),
                completed_at=datetime.fromisoformat(task_data['completed_at'].replace('Z', '+00:00')) if task_data.get('completed_at') else None,
                error_message=task_data.get('error_message'),
                retry_count=task_data.get('retry_count', 0)
            )
        return None
        
    except Exception as e:
        logger.error("Failed to get pending task", domain=domain, task_type=task_type, error=str(e))
        return None

async def save_async_task(self, task: AsyncTask) -> str:
    """Save async task"""
    try:
        task_dict = {
            'domain_name': task.domain_name,
            'task_id': task.task_id,
            'task_type': task.task_type.value,
            'status': task.status.value,
            'retry_count': task.retry_count
        }
        
        result = self.client.table('async_tasks').insert(task_dict).execute()
        return result.data[0]['id'] if result.data else None
        
    except Exception as e:
        logger.error("Failed to save async task", domain=task.domain_name, task_type=task.task_type, error=str(e))
        return None

async def update_async_task_status(self, task_id: str, status: AsyncTaskStatus, error_message: str = None) -> bool:
    """Update async task status"""
    try:
        update_data = {
            'status': status.value,
            'completed_at': datetime.utcnow().isoformat() if status == AsyncTaskStatus.COMPLETED else None,
            'error_message': error_message
        }
        
        result = self.client.table('async_tasks').update(update_data).eq('task_id', task_id).execute()
        return len(result.data) > 0
        
    except Exception as e:
        logger.error("Failed to update async task status", task_id=task_id, status=status, error=str(e))
        return False
```

### Phase 3: Enhanced Analysis Service (Week 3)

#### 3.1 Update Analysis Service
**File**: `backend/src/services/analysis_service.py`

```python
# Update analyze_domain method
async def analyze_domain(self, domain: str, report_id: str) -> None:
    """
    Perform complete domain analysis with mandatory detailed data collection
    """
    start_time = datetime.utcnow()
    
    try:
        logger.info("Starting comprehensive domain analysis", domain=domain, report_id=report_id)
        
        # Get existing report or create new one
        report = await self.db.get_report(domain)
        if not report:
            report = DomainAnalysisReport(
                domain_name=domain,
                status=AnalysisStatus.IN_PROGRESS,
                analysis_phase="essential"
            )
            await self.db.save_report(report)
        else:
            report.status = AnalysisStatus.IN_PROGRESS
            report.analysis_phase = "essential"
            report.error_message = None
            report.processing_time_seconds = None
            await self.db.save_report(report)
        
        # Phase 1: Essential data collection (parallel)
        logger.info("Phase 1: Collecting essential data", domain=domain)
        essential_tasks = [
            self.dataforseo_service.get_domain_analytics(domain),
            self.dataforseo_service.get_backlinks_summary(domain),
            self.wayback_service.get_domain_history(domain)
        ]
        
        dataforseo_data, backlinks_summary_data, wayback_data = await asyncio.gather(
            *essential_tasks, return_exceptions=True
        )
        
        # Handle essential data exceptions
        if isinstance(dataforseo_data, Exception):
            logger.error("DataForSEO essential data failed", domain=domain, error=str(dataforseo_data))
            dataforseo_data = None
        
        if isinstance(backlinks_summary_data, Exception):
            logger.error("Backlinks summary failed", domain=domain, error=str(backlinks_summary_data))
            backlinks_summary_data = None
        
        if isinstance(wayback_data, Exception):
            logger.error("Wayback data failed", domain=domain, error=str(wayback_data))
            wayback_data = None
        
        # Update report with essential data
        report.data_for_seo_metrics = self.dataforseo_service.parse_domain_metrics({
            "domain_rank": dataforseo_data.get("domain_rank", {}) if dataforseo_data else {},
            "backlinks_summary": backlinks_summary_data or {}
        }) if dataforseo_data or backlinks_summary_data else None
        
        report.wayback_machine_summary = self.wayback_service.parse_wayback_summary(wayback_data) if wayback_data else None
        report.analysis_phase = "detailed"
        await self.db.save_report(report)
        
        # Phase 2: Detailed data collection (async pattern)
        logger.info("Phase 2: Collecting detailed data", domain=domain)
        from services.dataforseo_async import DataForSEOAsyncService
        async_service = DataForSEOAsyncService()
        
        detailed_tasks = [
            async_service.get_detailed_backlinks_async(domain, 1000),
            async_service.get_detailed_keywords_async(domain, 1000),
            async_service.get_referring_domains_async(domain, 800)
        ]
        
        detailed_backlinks, detailed_keywords, referring_domains = await asyncio.gather(
            *detailed_tasks, return_exceptions=True
        )
        
        # Handle detailed data exceptions
        if isinstance(detailed_backlinks, Exception):
            logger.error("Detailed backlinks failed", domain=domain, error=str(detailed_backlinks))
            detailed_backlinks = None
        
        if isinstance(detailed_keywords, Exception):
            logger.error("Detailed keywords failed", domain=domain, error=str(detailed_keywords))
            detailed_keywords = None
        
        if isinstance(referring_domains, Exception):
            logger.error("Referring domains failed", domain=domain, error=str(referring_domains))
            referring_domains = None
        
        # Update detailed data availability
        report.detailed_data_available = {
            "backlinks": detailed_backlinks is not None,
            "keywords": detailed_keywords is not None,
            "referring_domains": referring_domains is not None
        }
        report.analysis_phase = "ai_analysis"
        await self.db.save_report(report)
        
        # Phase 3: AI Analysis with comprehensive data
        logger.info("Phase 3: Generating AI analysis", domain=domain)
        
        # Prepare comprehensive data for AI analysis
        analysis_data = {
            "analytics": {
                "domain_rank": report.data_for_seo_metrics.domain_rating_dr if report.data_for_seo_metrics else 0,
                "organic_traffic": report.data_for_seo_metrics.organic_traffic_est if report.data_for_seo_metrics else 0
            },
            "backlinks": {
                "total_count": report.data_for_seo_metrics.total_referring_domains if report.data_for_seo_metrics else 0,
                "backlinks_count": report.data_for_seo_metrics.total_backlinks if report.data_for_seo_metrics else 0,
                "items": detailed_backlinks.get("items", []) if detailed_backlinks else []
            },
            "referring_domains": {
                "items": referring_domains.get("items", []) if referring_domains else []
            },
            "keywords": {
                "items": detailed_keywords.get("items", []) if detailed_keywords else []
            },
            "wayback": report.wayback_machine_summary.dict() if report.wayback_machine_summary else {}
        }
        
        # Generate AI analysis with comprehensive data
        llm_data = await self.llm_service.generate_analysis(domain, analysis_data)
        
        if llm_data:
            report.llm_analysis = LLMAnalysis(**llm_data)
            report.analysis_phase = "completed"
            report.status = AnalysisStatus.COMPLETED
        else:
            report.error_message = "Failed to generate AI analysis"
            report.status = AnalysisStatus.FAILED
        
        # Calculate processing time
        end_time = datetime.utcnow()
        report.processing_time_seconds = (end_time - start_time).total_seconds()
        
        await self.db.save_report(report)
        
        logger.info("Domain analysis completed", 
                   domain=domain, 
                   status=report.status,
                   processing_time=report.processing_time_seconds,
                   detailed_data_available=report.detailed_data_available)
        
    except Exception as e:
        logger.error("Domain analysis failed", domain=domain, error=str(e))
        
        # Update report with error
        report.status = AnalysisStatus.FAILED
        report.error_message = str(e)
        report.processing_time_seconds = (datetime.utcnow() - start_time).total_seconds()
        await self.db.save_report(report)
```

#### 3.2 Enhanced LLM Analysis Prompt
**File**: `backend/src/services/external_apis.py`

```python
def _build_analysis_prompt(self, domain: str, data: Dict[str, Any]) -> str:
    """Enhanced prompt with comprehensive backlink quality analysis"""
    analytics = data.get("analytics", {})
    backlinks = data.get("backlinks", {})
    referring_domains = data.get("referring_domains", {})
    keywords = data.get("keywords", {})
    wayback = data.get("wayback", {})
    
    # Calculate quality metrics
    backlink_items = backlinks.get("items", [])
    referring_domain_items = referring_domains.get("items", [])
    keyword_items = keywords.get("items", [])
    
    # Backlink quality analysis
    high_authority_domains = sum(1 for domain in referring_domain_items if domain.get('domain_rank', 0) >= 70)
    total_referring_domains = len(referring_domain_items)
    authority_percentage = (high_authority_domains / total_referring_domains * 100) if total_referring_domains > 0 else 0
    
    # Keyword analysis
    high_difficulty_keywords = sum(1 for kw in keyword_items if kw.get('keyword_difficulty', 0) >= 70)
    total_keywords = len(keyword_items)
    difficulty_percentage = (high_difficulty_keywords / total_keywords * 100) if total_keywords > 0 else 0
    
    prompt = f"""
    Analyze the following domain data for {domain} and provide a comprehensive SEO analysis report.
    
    CRITICAL: You now have access to detailed backlink and keyword data. 
    Provide thorough quality assessment including:
    
    Domain Analytics:
    - Domain Rating (DR): {analytics.get('domain_rank', 'N/A')}
    - Organic Traffic: {analytics.get('organic_traffic', 'N/A')}
    - Total Referring Domains: {backlinks.get('total_count', 'N/A')}
    - Total Backlinks: {backlinks.get('backlinks_count', 'N/A')}
    
    BACKLINK QUALITY ANALYSIS:
    - Total Detailed Backlinks Analyzed: {len(backlink_items)}
    - High Authority Referring Domains (DR 70+): {high_authority_domains} ({authority_percentage:.1f}%)
    - Total Referring Domains Analyzed: {total_referring_domains}
    
    KEYWORD PORTFOLIO ANALYSIS:
    - Total Keywords Analyzed: {total_keywords}
    - High Difficulty Keywords (70+): {high_difficulty_keywords} ({difficulty_percentage:.1f}%)
    
    DETAILED BACKLINK QUALITY ASSESSMENT:
    1. Domain Authority Distribution:
       - Analyze the DR score distribution of referring domains
       - Identify presence of high-authority domains (DR 70+)
       - Calculate authority diversity score
    
    2. Geographic and Topical Diversity:
       - Assess geographic spread of referring domains
       - Evaluate topical relevance and diversity
       - Identify potential link farm patterns
    
    3. Anchor Text Analysis:
       - Analyze anchor text patterns for over-optimization
       - Identify branded vs. non-branded anchor text ratio
       - Assess anchor text diversity and naturalness
    
    4. Link Acquisition Patterns:
       - Evaluate link velocity and acquisition trends
       - Identify potential link building strategies
       - Assess link profile health indicators
    
    DETAILED KEYWORD ANALYSIS:
    1. Keyword Difficulty Distribution:
       - Analyze difficulty score distribution
       - Identify high-opportunity keywords
       - Assess competition landscape
    
    2. Search Volume vs. Competition:
       - Evaluate search volume distribution
       - Identify keyword gaps and opportunities
       - Assess ranking potential
    
    3. Branded vs. Non-Branded Mix:
       - Analyze branded keyword percentage
       - Evaluate brand authority indicators
       - Assess organic growth potential
    
    REFERRING DOMAIN DIVERSITY:
    - Domain Type Distribution: Analyze .com, .org, .edu, .gov distribution
    - Industry Relevance: Assess topical relevance of referring domains
    - Link Profile Health: Identify potential red flags or strengths
    
    Historical Data:
    - Total Captures: {wayback.get('total_captures', 'N/A')}
    - First Capture Year: {wayback.get('first_capture_year', 'N/A')}
    - Last Capture: {wayback.get('last_capture_date', 'N/A')}
    
    Please provide a JSON response with the following structure:
    {{
        "summary": "Brief overview of domain's SEO strength and weaknesses",
        "strengths": [
            "List of key strengths with supporting metrics"
        ],
        "weaknesses": [
            "List of areas for improvement with specific recommendations"
        ],
        "backlink_quality_score": "Score 1-10 with detailed explanation",
        "keyword_opportunity_score": "Score 1-10 with detailed explanation",
        "investment_recommendation": "Overall investment recommendation with reasoning",
        "key_metrics": {{
            "domain_authority": "Assessment of domain authority",
            "backlink_profile_health": "Assessment of backlink profile",
            "keyword_potential": "Assessment of keyword opportunities",
            "technical_seo": "Assessment of technical SEO factors"
        }},
        "recommendations": [
            "Specific actionable recommendations for improvement"
        ]
    }}
    """
    
    return prompt
```

### Phase 4: API Endpoint Updates (Week 4)

#### 4.1 Update Analysis Endpoints
**File**: `backend/src/api/routes/analysis.py`

```python
# Add new endpoint for detailed data retrieval
@router.get("/analyze/{domain}/detailed/{data_type}")
async def get_detailed_data(domain: str, data_type: str):
    """
    Get detailed analysis data for a specific domain and type
    """
    try:
        from models.domain_analysis import DetailedDataType
        
        # Validate data type
        try:
            data_type_enum = DetailedDataType(data_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid data type")
        
        db = get_database()
        detailed_data = await db.get_detailed_data(domain, data_type_enum)
        
        if not detailed_data:
            raise HTTPException(status_code=404, detail="Detailed data not found")
        
        return {
            "success": True,
            "data": detailed_data.json_data,
            "metadata": {
                "domain": detailed_data.domain_name,
                "data_type": detailed_data.data_type.value,
                "created_at": detailed_data.created_at.isoformat(),
                "expires_at": detailed_data.expires_at.isoformat() if detailed_data.expires_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get detailed data", domain=domain, data_type=data_type, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get detailed data")

# Update existing analyze endpoint to include phase information
@router.get("/analyze/{domain}", response_model=AnalysisResponse)
async def get_analysis_status(domain: str):
    """
    Get analysis status and results with phase information
    """
    try:
        db = get_database()
        report = await db.get_report(domain)
        
        if not report:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        if report.status == AnalysisStatus.FAILED:
            return AnalysisResponse(
                success=False,
                message=f"Analysis failed: {report.error_message}",
                report_id=domain,
                analysis_phase=report.analysis_phase
            )
        elif report.status == AnalysisStatus.COMPLETED:
            return AnalysisResponse(
                success=True,
                message="Analysis completed successfully",
                report_id=domain,
                analysis_phase=report.analysis_phase,
                detailed_data_available=report.detailed_data_available
            )
        else:
            return AnalysisResponse(
                success=True,
                message=f"Analysis in progress - {report.analysis_phase} phase",
                report_id=domain,
                analysis_phase=report.analysis_phase
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get analysis status", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get analysis status")
```

#### 4.2 Update Response Models
**File**: `backend/src/models/domain_analysis.py`

```python
# Update AnalysisResponse model
class AnalysisResponse(BaseModel):
    success: bool
    message: str
    report_id: str
    estimated_completion_time: Optional[int] = None
    analysis_phase: Optional[str] = None
    detailed_data_available: Optional[Dict[str, bool]] = None
```

### Phase 5: Frontend Updates (Week 5)

#### 5.1 Update Frontend API Service
**File**: `frontend/src/services/api.tsx`

```typescript
// Add new methods for detailed data retrieval
async getDetailedData(domain: string, dataType: 'backlinks' | 'keywords' | 'referring_domains'): Promise<any> {
  const response = await this.client.get(`/analyze/${domain}/detailed/${dataType}`);
  return response.data;
}

// Update analyzeDomain method to handle phase information
async analyzeDomain(domain: string): Promise<AnalysisResponse> {
  const response = await this.client.post('/analyze', { domain });
  return response.data;
}

// Add method to check analysis phase
async getAnalysisPhase(domain: string): Promise<string> {
  const response = await this.client.get(`/analyze/${domain}`);
  return response.data.analysis_phase || 'unknown';
}
```

#### 5.2 Update Frontend Components
**File**: `frontend/src/components/LLMAnalysis.tsx`

```typescript
// Add detailed data loading indicators
const [loadingDetailedData, setLoadingDetailedData] = useState(false);
const [detailedDataAvailable, setDetailedDataAvailable] = useState({
  backlinks: false,
  keywords: false,
  referring_domains: false
});

// Add method to load detailed data on demand
const loadDetailedData = async (dataType: string) => {
  setLoadingDetailedData(true);
  try {
    const data = await api.getDetailedData(domain, dataType);
    // Process and display detailed data
    console.log(`Loaded detailed ${dataType}:`, data);
  } catch (error) {
    console.error(`Failed to load detailed ${dataType}:`, error);
  } finally {
    setLoadingDetailedData(false);
  }
};
```

### Phase 6: Testing and Optimization (Week 6)

#### 6.1 Unit Tests
**File**: `backend/tests/unit/test_dataforseo_async.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from services.dataforseo_async import DataForSEOAsyncService
from models.domain_analysis import DetailedDataType

@pytest.mark.asyncio
async def test_get_detailed_backlinks_async():
    """Test async backlinks retrieval"""
    service = DataForSEOAsyncService()
    
    with patch.object(service, '_execute_async_task') as mock_execute:
        mock_execute.return_value = {"items": [{"url": "test.com", "domain_rank": 80}]}
        
        result = await service.get_detailed_backlinks_async("example.com")
        
        assert result is not None
        assert "items" in result
        mock_execute.assert_called_once()

@pytest.mark.asyncio
async def test_task_polling():
    """Test task polling mechanism"""
    service = DataForSEOAsyncService()
    
    with patch.object(service, '_is_task_ready') as mock_ready:
        mock_ready.side_effect = [False, False, True]  # Ready on third attempt
        
        with patch.object(service, '_get_task_results') as mock_results:
            mock_results.return_value = {"items": []}
            
            result = await service._wait_for_task_completion("example.com", DetailedDataType.BACKLINKS, "task123")
            
            assert result is not None
            assert mock_ready.call_count == 3
```

#### 6.2 Integration Tests
**File**: `backend/tests/integration/test_analysis_workflow.py`

```python
import pytest
from services.analysis_service import AnalysisService
from models.domain_analysis import AnalysisStatus

@pytest.mark.asyncio
async def test_complete_analysis_workflow():
    """Test complete analysis workflow with detailed data"""
    service = AnalysisService()
    
    # Mock external services
    with patch.object(service.dataforseo_service, 'get_domain_analytics') as mock_analytics:
        with patch.object(service.wayback_service, 'get_domain_history') as mock_wayback:
            with patch.object(service.llm_service, 'generate_analysis') as mock_llm:
                
                # Setup mocks
                mock_analytics.return_value = {"domain_rank": {"dr": 50}}
                mock_wayback.return_value = {"total_captures": 100}
                mock_llm.return_value = {"summary": "Test analysis"}
                
                # Run analysis
                await service.analyze_domain("example.com", "test-report-id")
                
                # Verify results
                report = await service.db.get_report("example.com")
                assert report.status == AnalysisStatus.COMPLETED
                assert report.analysis_phase == "completed"
                assert report.detailed_data_available["backlinks"] is True
```

### Phase 7: Migration and Deployment (Week 7)

#### 7.1 Database Migration Script
**File**: `backend/scripts/migrate_to_async.py`

```python
"""
Migration script to transition existing reports to new async workflow
"""

import asyncio
from services.database import get_database
from services.analysis_service import AnalysisService

async def migrate_existing_reports():
    """Migrate existing reports to new workflow"""
    db = get_database()
    analysis_service = AnalysisService()
    
    # Get all existing reports
    reports = await db.get_all_reports()
    
    for report in reports:
        if report.status == AnalysisStatus.COMPLETED:
            # Re-run analysis with new workflow
            logger.info(f"Migrating report for {report.domain_name}")
            await analysis_service.analyze_domain(report.domain_name, report.id)
    
    logger.info("Migration completed")

if __name__ == "__main__":
    asyncio.run(migrate_existing_reports())
```

#### 7.2 Configuration Updates
**File**: `backend/src/utils/config.py`

```python
# Add new configuration options
class Settings(BaseSettings):
    # ... existing settings ...
    
    # DataForSEO Async Configuration
    DATAFORSEO_ASYNC_POLL_INTERVAL: int = 2  # seconds
    DATAFORSEO_ASYNC_MAX_ATTEMPTS: int = 30  # 1 minute max
    DATAFORSEO_ASYNC_TIMEOUT: int = 30  # seconds
    
    # Detailed Data Configuration
    DETAILED_DATA_CACHE_HOURS: int = 24  # hours
    DETAILED_DATA_LIMITS: Dict[str, int] = {
        "backlinks": 1000,
        "keywords": 1000,
        "referring_domains": 800
    }
    
    # Analysis Phase Configuration
    ANALYSIS_PHASES: List[str] = ["essential", "detailed", "ai_analysis", "completed"]
```

## Cost Analysis and Benefits

### Current Costs (Per Domain Analysis)
- Backlinks Summary (Live): ~$0.50
- Detailed Backlinks (Live): ~$2.00
- Keywords (Live): ~$1.50
- Referring Domains (Live): ~$2.00
- **Total: ~$6.00 per domain**

### New Costs (Per Domain Analysis)
- Backlinks Summary (Live): ~$0.50
- Detailed Backlinks (Async): ~$0.40
- Keywords (Async): ~$0.30
- Referring Domains (Async): ~$0.40
- **Total: ~$1.60 per domain**

### Cost Savings
- **73% reduction** in DataForSEO API costs
- **$4.40 saved per domain analysis**
- For 100 domains/month: **$440/month savings**

### Additional Benefits
1. **Complete AI Analysis**: Always includes detailed backlink quality assessment
2. **Better User Experience**: Faster subsequent analyses using cached data
3. **Scalability**: Async pattern supports bulk analysis operations
4. **Data Persistence**: Detailed data stored for future analysis and comparison
5. **Improved Accuracy**: More comprehensive data leads to better AI insights

## Risk Mitigation

### Technical Risks
1. **Async Task Failures**: Implement retry logic and fallback mechanisms
2. **Data Consistency**: Use database transactions for atomic operations
3. **API Rate Limits**: Implement proper queuing and throttling

### Business Risks
1. **Increased Analysis Time**: Initial analysis takes longer but subsequent analyses are faster
2. **Storage Costs**: Additional Supabase storage for detailed data (minimal impact)
3. **Complexity**: More complex codebase requires better testing and monitoring

## Success Metrics

### Technical Metrics
- API cost reduction: Target 70%+ reduction
- Analysis completion rate: Target 95%+ success rate
- Data freshness: Target 24-hour cache validity
- Response time: Target <30 seconds for cached data

### Business Metrics
- User satisfaction: Improved analysis quality
- Cost efficiency: Reduced operational costs
- Scalability: Support for bulk analysis operations
- Data quality: Comprehensive backlink and keyword analysis

## Implementation Timeline

| Week | Phase | Deliverables | Dependencies |
|------|-------|-------------|--------------|
| 1 | Database Schema | Migration scripts, new tables | Supabase access |
| 2 | Async Service | DataForSEO async implementation | Database schema |
| 3 | Analysis Service | Enhanced analysis workflow | Async service |
| 4 | API Updates | New endpoints, response models | Analysis service |
| 5 | Frontend Updates | UI improvements, data loading | API updates |
| 6 | Testing | Unit tests, integration tests | All components |
| 7 | Migration | Production deployment | Testing complete |

## Conclusion

This implementation plan addresses all identified issues while providing significant cost savings and improved functionality. The phased approach ensures minimal disruption to existing operations while gradually introducing the new capabilities. The async pattern implementation alone will provide 70%+ cost savings while enabling more comprehensive AI analysis.

The plan is designed to be implemented incrementally, with each phase building upon the previous one. This approach allows for early validation of the cost savings and functionality improvements while maintaining system stability.





