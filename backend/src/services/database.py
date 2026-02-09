"""
Database service for Supabase integration
"""

from supabase import create_client, Client
from typing import Optional, Dict, Any, List
import structlog
import re
from datetime import datetime, timedelta, timezone

from utils.config import get_settings
from models.domain_analysis import (
    DomainAnalysisReport, RawDataCache, DataSource, 
    DetailedAnalysisData, AsyncTask, AsyncTaskStatus, 
    DetailedDataType, AnalysisModeConfig, ProgressInfo,
    BulkDomainInput, BulkDomainAnalysis, BulkDomainSyncResult,
    NamecheapDomain
)

logger = structlog.get_logger()


class DatabaseService:
    """Database service for Supabase operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Supabase client"""
        try:
            from supabase import create_client
            # Try to import SyncClientOptions, available in newer supabase versions
            try:
                from supabase.lib.client_options import SyncClientOptions
                HAS_CLIENT_OPTIONS = True
            except ImportError:
                HAS_CLIENT_OPTIONS = False
            
            import httpx
            
            # Configure HTTP client with SSL verification setting and increased timeout
            timeout = httpx.Timeout(300.0, connect=30.0)  # 5 minutes for requests, 30s for connection
            
            # Default options
            options = None
            
            if HAS_CLIENT_OPTIONS:
                if not getattr(self.settings, 'SUPABASE_VERIFY_SSL', True):
                    # Disable SSL verification for self-hosted instances with self-signed certificates
                    custom_client = httpx.Client(verify=False, timeout=timeout)
                    logger.warning("SSL verification disabled for Supabase client (self-hosted instance)")
                    # Create client options with custom httpx client
                    options = SyncClientOptions(httpx_client=custom_client)
                else:
                    # Create client with increased timeout
                    custom_client = httpx.Client(timeout=timeout)
                    options = SyncClientOptions(httpx_client=custom_client)
            
            # Use service role key for admin operations
            key = self.settings.SUPABASE_SERVICE_ROLE_KEY
            if not key:
                logger.warning("SUPABASE_SERVICE_ROLE_KEY not found, falling back to SUPABASE_KEY. RLS policies may fail!")
                key = self.settings.SUPABASE_KEY
            else:
                logger.info("Initializing Supabase client with SERVICE_ROLE_KEY")

            if options:
                self.client = create_client(
                    self.settings.SUPABASE_URL,
                    key,
                    options=options
                )
            else:
                self.client = create_client(
                    self.settings.SUPABASE_URL,
                    key
                )
            
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"DEBUG: Failed to initialize Supabase client: {e}")
            logger.error("Failed to initialize Supabase client", error=str(e))
            # Fallback to None for now
            self.client = None
            logger.warning("Supabase client disabled, using fallback mode")
    
    async def init_database(self):
        """Initialize database tables and indexes"""
        try:
            # Create tables if they don't exist
            await self._create_tables()
            await self._create_indexes()
            logger.info("Database initialization completed")
        except Exception as e:
            logger.error("Database initialization failed", error=str(e))
            raise
    
    async def _create_tables(self):
        """Create database tables"""
        # This would typically be done via Supabase migrations
        # For now, we'll assume tables exist or create them via SQL
        tables_sql = """
        -- Create reports table
        CREATE TABLE IF NOT EXISTS reports (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            domain_name VARCHAR(255) NOT NULL UNIQUE,
            analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            data_for_seo_metrics JSONB,
            wayback_machine_summary JSONB,
            llm_analysis JSONB,
            historical_data JSONB,
            raw_data_links JSONB,
            processing_time_seconds FLOAT,
            error_message TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Create raw_data_cache table
        CREATE TABLE IF NOT EXISTS raw_data_cache (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            domain_name VARCHAR(255) NOT NULL,
            api_source VARCHAR(50) NOT NULL,
            json_data JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE,
            UNIQUE(domain_name, api_source)
        );
        
        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_reports_domain_name ON reports(domain_name);
        CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
        CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at);
        CREATE INDEX IF NOT EXISTS idx_raw_data_cache_domain_source ON raw_data_cache(domain_name, api_source);
        CREATE INDEX IF NOT EXISTS idx_raw_data_cache_expires_at ON raw_data_cache(expires_at);
        """
        
        # Execute SQL via Supabase
        result = self.client.rpc('exec_sql', {'sql': tables_sql})
        logger.info("Database tables created/verified")
    
    async def _create_indexes(self):
        """Create database indexes for performance"""
        # Indexes are created in _create_tables method
        pass
    
    async def save_report(self, report: DomainAnalysisReport) -> str:
        """Save domain analysis report to database"""
        try:
            report_data = report.dict()
            report_data['analysis_timestamp'] = report_data['analysis_timestamp'].isoformat()
            
            # Convert datetime objects in nested models to ISO strings
            if report_data.get('wayback_machine_summary') and report_data['wayback_machine_summary'].get('last_capture_date'):
                if hasattr(report_data['wayback_machine_summary']['last_capture_date'], 'isoformat'):
                    report_data['wayback_machine_summary']['last_capture_date'] = report_data['wayback_machine_summary']['last_capture_date'].isoformat()
            
            result = self.client.table('reports').upsert({
                'domain_name': report.domain_name,
                'analysis_timestamp': report_data['analysis_timestamp'],
                'status': report.status.value,
                'data_for_seo_metrics': report_data.get('data_for_seo_metrics'),
                'wayback_machine_summary': report_data.get('wayback_machine_summary'),
                'llm_analysis': report_data.get('llm_analysis'),
                'historical_data': report.historical_data.model_dump(mode='json') if report.historical_data else None,
                'raw_data_links': report_data.get('raw_data_links'),
                'detailed_data_available': report_data.get('detailed_data_available'),
                'analysis_phase': report_data.get('analysis_phase'),
                'progress_data': report.progress_data.dict() if report.progress_data else None,
                'processing_time_seconds': report.processing_time_seconds,
                'error_message': report.error_message,
                'updated_at': datetime.utcnow().isoformat()
            }, on_conflict='domain_name').execute()
            
            report_id = result.data[0]['id'] if result.data else None
            logger.info("Report saved successfully", domain=report.domain_name, report_id=report_id)
            return report_id
            
        except Exception as e:
            logger.error("Failed to save report", domain=report.domain_name, error=str(e))
            raise
    
    async def get_report(self, domain_name: str) -> Optional[DomainAnalysisReport]:
        """Get domain analysis report by domain name"""
        try:
            result = self.client.table('reports').select('*').eq('domain_name', domain_name).execute()
            
            if not result.data:
                return None
            
            report_data = result.data[0]
            
            # Convert back to DomainAnalysisReport object
            report = DomainAnalysisReport(
                domain_name=report_data['domain_name'],
                analysis_timestamp=datetime.fromisoformat(report_data['analysis_timestamp'].replace('Z', '+00:00')),
                status=report_data['status'],
                data_for_seo_metrics=report_data.get('data_for_seo_metrics'),
                wayback_machine_summary=report_data.get('wayback_machine_summary'),
                llm_analysis=report_data.get('llm_analysis'),
                historical_data=report_data.get('historical_data'),
                raw_data_links=report_data.get('raw_data_links'),
                detailed_data_available=report_data.get('detailed_data_available'),
                analysis_phase=report_data.get('analysis_phase'),
                progress_data=report_data.get('progress_data'),
                processing_time_seconds=report_data.get('processing_time_seconds'),
                error_message=report_data.get('error_message')
            )
            
            logger.info("Report retrieved successfully", domain=domain_name)
            return report
            
        except Exception as e:
            logger.error("Failed to get report", domain=domain_name, error=str(e))
            raise
    
    async def save_raw_data(self, domain_name: str, api_source: DataSource, data: Dict[str, Any]) -> str:
        """Save raw API data to cache"""
        try:
            expires_at = datetime.utcnow() + timedelta(seconds=get_settings().CACHE_TTL_SECONDS)
            
            result = self.client.table('raw_data_cache').upsert({
                'domain_name': domain_name,
                'api_source': api_source.value,
                'json_data': data,
                'expires_at': expires_at.isoformat()
            }).execute()
            
            cache_id = result.data[0]['id'] if result.data else None
            logger.info("Raw data cached successfully", domain=domain_name, source=api_source.value)
            return cache_id
            
        except Exception as e:
            logger.error("Failed to save raw data", domain=domain_name, source=api_source.value, error=str(e))
            raise
    
    async def get_raw_data(self, domain_name: str, api_source: DataSource) -> Optional[Dict[str, Any]]:
        """Get cached raw API data"""
        try:
            result = self.client.table('raw_data_cache').select('*').eq('domain_name', domain_name).eq('api_source', api_source.value).execute()
            
            if not result.data:
                return None
            
            cache_data = result.data[0]
            
            # Check if data is expired
            if cache_data.get('expires_at'):
                expires_at = datetime.fromisoformat(cache_data['expires_at'].replace('Z', '+00:00'))
                # Make utcnow timezone-aware for comparison
                now_utc = datetime.utcnow().replace(tzinfo=expires_at.tzinfo)
                if now_utc > expires_at:
                    # Delete expired data
                    await self.delete_raw_data(domain_name, api_source)
                    return None
            
            logger.info("Raw data retrieved from cache", domain=domain_name, source=api_source.value)
            return cache_data['json_data']
            
        except Exception as e:
            logger.error("Failed to get raw data", domain=domain_name, source=api_source.value, error=str(e))
            raise
    
    async def delete_raw_data(self, domain_name: str, api_source: DataSource):
        """Delete cached raw data"""
        try:
            self.client.table('raw_data_cache').delete().eq('domain_name', domain_name).eq('api_source', api_source.value).execute()
            logger.info("Raw data deleted from cache", domain=domain_name, source=api_source.value)
        except Exception as e:
            logger.error("Failed to delete raw data", domain=domain_name, source=api_source.value, error=str(e))
            raise
    
    async def cleanup_expired_data(self):
        """Clean up expired cached data"""
        try:
            result = self.client.table('raw_data_cache').delete().lt('expires_at', datetime.utcnow().isoformat()).execute()
            logger.info("Expired data cleaned up", deleted_count=len(result.data) if result.data else 0)
        except Exception as e:
            logger.error("Failed to cleanup expired data", error=str(e))
            raise
    
    # Detailed Data Storage Methods
    async def save_detailed_data(self, detailed_data: DetailedAnalysisData) -> str:
        """Save detailed analysis data to database"""
        try:
            expires_at = None
            if detailed_data.expires_at:
                expires_at = detailed_data.expires_at.isoformat()
            
            result = self.client.table('detailed_analysis_data').upsert({
                'domain_name': detailed_data.domain_name,
                'data_type': detailed_data.data_type.value,
                'json_data': detailed_data.json_data,
                'task_id': detailed_data.task_id,
                'data_source': detailed_data.data_source,
                'expires_at': expires_at
            }, on_conflict='domain_name,data_type').execute()
            
            data_id = result.data[0]['id'] if result.data else None
            logger.info("Detailed data saved successfully", 
                       domain=detailed_data.domain_name, 
                       data_type=detailed_data.data_type.value,
                       data_id=data_id)
            return data_id
            
        except Exception as e:
            logger.error("Failed to save detailed data", 
                        domain=detailed_data.domain_name, 
                        data_type=detailed_data.data_type.value, 
                        error=str(e))
            raise
    
    async def get_detailed_data(self, domain_name: str, data_type: DetailedDataType) -> Optional[DetailedAnalysisData]:
        """Get detailed analysis data by domain and type"""
        try:
            result = self.client.table('detailed_analysis_data').select('*').eq('domain_name', domain_name).eq('data_type', data_type.value).execute()
            
            if not result.data:
                return None
            
            data = result.data[0]
            
            # Check if data is expired
            if data.get('expires_at'):
                expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
                now_utc = datetime.utcnow().replace(tzinfo=expires_at.tzinfo)
                if now_utc > expires_at:
                    await self.delete_detailed_data(domain_name, data_type)
                    return None
            
            detailed_data = DetailedAnalysisData(
                id=data['id'],
                domain_name=data['domain_name'],
                data_type=DetailedDataType(data['data_type']),
                json_data=data['json_data'],
                task_id=data.get('task_id'),
                data_source=data.get('data_source', 'dataforseo'),
                created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None,
                expires_at=datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00')) if data.get('expires_at') else None
            )
            
            logger.info("Detailed data retrieved successfully", domain=domain_name, data_type=data_type.value)
            return detailed_data
            
        except Exception as e:
            logger.error("Failed to get detailed data", domain=domain_name, data_type=data_type.value, error=str(e))
            raise
    
    async def delete_detailed_data(self, domain_name: str, data_type: DetailedDataType):
        """Delete detailed analysis data"""
        try:
            self.client.table('detailed_analysis_data').delete().eq('domain_name', domain_name).eq('data_type', data_type.value).execute()
            logger.info("Detailed data deleted", domain=domain_name, data_type=data_type.value)
        except Exception as e:
            logger.error("Failed to delete detailed data", domain=domain_name, data_type=data_type.value, error=str(e))
            raise
    
    # Async Task Tracking Methods
    async def save_async_task(self, async_task: AsyncTask) -> str:
        """Save async task to database"""
        try:
            result = self.client.table('async_tasks').upsert({
                'domain_name': async_task.domain_name,
                'task_id': async_task.task_id,
                'task_type': async_task.task_type.value,
                'status': async_task.status.value,
                'error_message': async_task.error_message,
                'retry_count': async_task.retry_count
            }, on_conflict='task_id').execute()
            
            task_id = result.data[0]['id'] if result.data else None
            logger.info("Async task saved successfully", 
                       domain=async_task.domain_name, 
                       task_id=async_task.task_id,
                       status=async_task.status.value)
            return task_id
            
        except Exception as e:
            logger.error("Failed to save async task", 
                        domain=async_task.domain_name, 
                        task_id=async_task.task_id, 
                        error=str(e))
            raise
    
    async def get_async_task(self, task_id: str) -> Optional[AsyncTask]:
        """Get async task by task ID"""
        try:
            result = self.client.table('async_tasks').select('*').eq('task_id', task_id).execute()
            
            if not result.data:
                return None
            
            task_data = result.data[0]
            
            async_task = AsyncTask(
                id=task_data['id'],
                domain_name=task_data['domain_name'],
                task_id=task_data['task_id'],
                task_type=DetailedDataType(task_data['task_type']),
                status=AsyncTaskStatus(task_data['status']),
                created_at=datetime.fromisoformat(task_data['created_at'].replace('Z', '+00:00')) if task_data.get('created_at') else None,
                completed_at=datetime.fromisoformat(task_data['completed_at'].replace('Z', '+00:00')) if task_data.get('completed_at') else None,
                error_message=task_data.get('error_message'),
                retry_count=task_data.get('retry_count', 0)
            )
            
            logger.info("Async task retrieved successfully", task_id=task_id)
            return async_task
            
        except Exception as e:
            logger.error("Failed to get async task", task_id=task_id, error=str(e))
            raise
    
    async def get_pending_task(self, domain_name: str, task_type: DetailedDataType) -> Optional[AsyncTask]:
        """Get pending async task for domain and type"""
        try:
            result = self.client.table('async_tasks').select('*').eq('domain_name', domain_name).eq('task_type', task_type.value).eq('status', 'pending').execute()
            
            if not result.data:
                return None
            
            task_data = result.data[0]
            
            async_task = AsyncTask(
                id=task_data['id'],
                domain_name=task_data['domain_name'],
                task_id=task_data['task_id'],
                task_type=DetailedDataType(task_data['task_type']),
                status=AsyncTaskStatus(task_data['status']),
                created_at=datetime.fromisoformat(task_data['created_at'].replace('Z', '+00:00')) if task_data.get('created_at') else None,
                completed_at=datetime.fromisoformat(task_data['completed_at'].replace('Z', '+00:00')) if task_data.get('completed_at') else None,
                error_message=task_data.get('error_message'),
                retry_count=task_data.get('retry_count', 0)
            )
            
            logger.info("Pending async task retrieved", domain=domain_name, task_type=task_type.value)
            return async_task
            
        except Exception as e:
            logger.error("Failed to get pending async task", domain=domain_name, task_type=task_type.value, error=str(e))
            raise
    
    async def update_async_task_status(self, task_id: str, status: AsyncTaskStatus, error_message: str = None):
        """Update async task status"""
        try:
            update_data = {
                'status': status.value,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if status == AsyncTaskStatus.COMPLETED:
                update_data['completed_at'] = datetime.utcnow().isoformat()
            elif status == AsyncTaskStatus.FAILED and error_message:
                update_data['error_message'] = error_message
            
            self.client.table('async_tasks').update(update_data).eq('task_id', task_id).execute()
            
            logger.info("Async task status updated", task_id=task_id, status=status.value)
            
        except Exception as e:
            logger.error("Failed to update async task status", task_id=task_id, status=status.value, error=str(e))
            raise
    
    # Analysis Mode Configuration Methods
    async def get_mode_config(self, domain_name: str = None) -> Optional[AnalysisModeConfig]:
        """Get analysis mode configuration for domain or global"""
        try:
            query = self.client.table('analysis_mode_config').select('*')
            
            if domain_name:
                query = query.eq('domain_name', domain_name)
            else:
                query = query.is_('domain_name', 'null')
            
            result = query.execute()
            
            if not result.data:
                return None
            
            config_data = result.data[0]
            
            config = AnalysisModeConfig(
                id=config_data['id'],
                domain_name=config_data.get('domain_name'),
                mode_preference=config_data['mode_preference'],
                async_enabled=config_data['async_enabled'],
                cache_ttl_hours=config_data['cache_ttl_hours'],
                manual_refresh_enabled=config_data['manual_refresh_enabled'],
                progress_indicators_enabled=config_data['progress_indicators_enabled'],
                created_at=datetime.fromisoformat(config_data['created_at'].replace('Z', '+00:00')) if config_data.get('created_at') else None,
                updated_at=datetime.fromisoformat(config_data['updated_at'].replace('Z', '+00:00')) if config_data.get('updated_at') else None
            )
            
            logger.info("Mode config retrieved", domain=domain_name)
            return config
            
        except Exception as e:
            logger.error("Failed to get mode config", domain=domain_name, error=str(e))
            raise
    
    async def save_mode_config(self, config: AnalysisModeConfig) -> str:
        """Save analysis mode configuration"""
        try:
            result = self.client.table('analysis_mode_config').upsert({
                'domain_name': config.domain_name,
                'mode_preference': config.mode_preference.value,
                'async_enabled': config.async_enabled,
                'cache_ttl_hours': config.cache_ttl_hours,
                'manual_refresh_enabled': config.manual_refresh_enabled,
                'progress_indicators_enabled': config.progress_indicators_enabled
            }, on_conflict='domain_name').execute()
            
            config_id = result.data[0]['id'] if result.data else None
            logger.info("Mode config saved successfully", domain=config.domain_name, config_id=config_id)
            return config_id
            
        except Exception as e:
            logger.error("Failed to save mode config", domain=config.domain_name, error=str(e))
            raise

    async def delete_domain_analysis(self, domain_name: str) -> bool:
        """
        Delete all records related to a domain analysis
        This includes:
        - Main report record
        - Detailed analysis data (backlinks, keywords, referring domains)
        - Raw data cache
        - Async tasks
        - Mode configuration
        """
        try:
            logger.info("Starting domain analysis deletion", domain=domain_name)
            deleted_count = 0
            
            # Check if client is available
            if not self.client:
                logger.error("Supabase client not available", domain=domain_name)
                raise Exception("Supabase client not available")
            
            # Delete detailed analysis data
            try:
                logger.info("Attempting to delete detailed analysis data", domain=domain_name)
                detailed_data_result = self.client.table('detailed_analysis_data').delete().eq('domain_name', domain_name).execute()
                deleted_count += len(detailed_data_result.data) if detailed_data_result.data else 0
                logger.info("Deleted detailed analysis data", domain=domain_name, count=len(detailed_data_result.data) if detailed_data_result.data else 0, result_data=detailed_data_result.data)
            except Exception as e:
                logger.error("Failed to delete detailed analysis data", domain=domain_name, error=str(e))
                raise
            
            # Delete raw data cache
            cache_result = self.client.table('raw_data_cache').delete().eq('domain_name', domain_name).execute()
            deleted_count += len(cache_result.data) if cache_result.data else 0
            logger.info("Deleted raw data cache", domain=domain_name, count=len(cache_result.data) if cache_result.data else 0)
            
            # Delete async tasks
            tasks_result = self.client.table('async_tasks').delete().eq('domain_name', domain_name).execute()
            deleted_count += len(tasks_result.data) if tasks_result.data else 0
            logger.info("Deleted async tasks", domain=domain_name, count=len(tasks_result.data) if tasks_result.data else 0)
            
            # Delete mode configuration
            config_result = self.client.table('analysis_mode_config').delete().eq('domain_name', domain_name).execute()
            deleted_count += len(config_result.data) if config_result.data else 0
            logger.info("Deleted mode configuration", domain=domain_name, count=len(config_result.data) if config_result.data else 0)
            
            # Delete main report (this should be last to maintain referential integrity)
            report_result = self.client.table('reports').delete().eq('domain_name', domain_name).execute()
            deleted_count += len(report_result.data) if report_result.data else 0
            logger.info("Deleted main report", domain=domain_name, count=len(report_result.data) if report_result.data else 0)
            
            logger.info("Domain analysis deletion completed", domain=domain_name, total_deleted=deleted_count)
            return deleted_count > 0
            
        except Exception as e:
            logger.error("Failed to delete domain analysis", domain=domain_name, error=str(e))
            raise
    
    # Bulk Domain Analysis Methods
    async def sync_bulk_domains(self, domains: List[BulkDomainInput]) -> BulkDomainSyncResult:
        """
        Sync bulk domain list to Supabase
        - Create new records for missing domains
        - Update provider for existing records (preserve backlinks_bulk_page_summary)
        - Return sync results
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            result = BulkDomainSyncResult(total_count=len(domains))
            
            for domain_input in domains:
                try:
                    # Check if domain exists
                    existing = self.client.table('bulk_domain_analysis').select('*').eq('domain_name', domain_input.domain).execute()
                    
                    if existing.data and len(existing.data) > 0:
                        # Domain exists - update only if needed
                        existing_record = existing.data[0]
                        existing_summary = existing_record.get('backlinks_bulk_page_summary')
                        
                        # Only update provider, preserve summary data
                        update_data = {
                            'updated_at': datetime.utcnow().isoformat()
                        }
                        
                        # Update provider if it's different
                        if domain_input.provider and existing_record.get('provider') != domain_input.provider:
                            update_data['provider'] = domain_input.provider
                        
                        # Only update if there's something to update
                        if len(update_data) > 1:  # More than just updated_at
                            self.client.table('bulk_domain_analysis').update(update_data).eq('domain_name', domain_input.domain).execute()
                            result.updated_count += 1
                            result.updated_domains.append(domain_input.domain)
                            logger.info("Updated bulk domain", domain=domain_input.domain, has_summary=existing_summary is not None)
                        else:
                            result.skipped_count += 1
                            result.skipped_domains.append(domain_input.domain)
                    else:
                        # Domain doesn't exist - create new record
                        new_record = {
                            'domain_name': domain_input.domain,
                            'provider': domain_input.provider,
                            'backlinks_bulk_page_summary': None
                        }
                        self.client.table('bulk_domain_analysis').insert(new_record).execute()
                        result.created_count += 1
                        result.created_domains.append(domain_input.domain)
                        logger.info("Created bulk domain", domain=domain_input.domain)
                        
                except Exception as e:
                    logger.error("Failed to sync domain", domain=domain_input.domain, error=str(e))
                    result.skipped_count += 1
                    result.skipped_domains.append(domain_input.domain)
            
            logger.info("Bulk domain sync completed", 
                       created=result.created_count, 
                       updated=result.updated_count, 
                       skipped=result.skipped_count)
            return result
            
        except Exception as e:
            logger.error("Failed to sync bulk domains", error=str(e))
            raise
    
    async def get_bulk_domains_missing_summary(self) -> List[str]:
        """
        Get list of domain names that are missing backlinks_bulk_page_summary data
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            result = self.client.table('bulk_domain_analysis').select('domain_name').is_('backlinks_bulk_page_summary', 'null').execute()
            
            domains = [row['domain_name'] for row in result.data] if result.data else []
            logger.info("Found domains missing summary", count=len(domains))
            return domains
            
        except Exception as e:
            logger.error("Failed to get domains missing summary", error=str(e))
            raise
    
    async def get_bulk_domains_by_names(self, domain_names: List[str]) -> List[BulkDomainAnalysis]:
        """
        Get bulk domain analysis records by domain names
        
        Args:
            domain_names: List of domain names to query
            
        Returns:
            List of BulkDomainAnalysis records
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            if not domain_names:
                return []
            
            # Query in batches (Supabase has limits on IN clause size)
            batch_size = 100
            all_records = []
            
            for i in range(0, len(domain_names), batch_size):
                batch = domain_names[i:i + batch_size]
                result = self.client.table('bulk_domain_analysis').select('*').in_('domain_name', batch).execute()
                
                if result.data:
                    for row in result.data:
                        # Parse backlinks_bulk_page_summary if present
                        summary = None
                        if row.get('backlinks_bulk_page_summary'):
                            try:
                                from models.domain_analysis import BulkPageSummaryResult
                                summary = BulkPageSummaryResult(**row['backlinks_bulk_page_summary'])
                            except Exception as e:
                                logger.warning("Failed to parse summary", domain=row.get('domain_name'), error=str(e))
                        
                        record = BulkDomainAnalysis(
                            id=row.get('id'),
                            domain_name=row['domain_name'],
                            provider=row.get('provider'),
                            backlinks_bulk_page_summary=summary,
                            created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')) if row.get('created_at') else None,
                            updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00')) if row.get('updated_at') else None
                        )
                        all_records.append(record)
            
            logger.info("Retrieved bulk domains by names", requested=len(domain_names), found=len(all_records))
            return all_records
            
        except Exception as e:
            logger.error("Failed to get bulk domains by names", error=str(e))
            raise
    
    async def save_bulk_page_summary(self, domain: str, summary_data: Dict[str, Any]) -> str:
        """
        Save bulk page summary data for a domain
        Preserves other fields (provider, etc.)
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            result = self.client.table('bulk_domain_analysis').update({
                'backlinks_bulk_page_summary': summary_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('domain_name', domain).execute()
            
            record_id = result.data[0]['id'] if result.data else None
            logger.info("Saved bulk page summary", domain=domain, record_id=record_id)
            return record_id
            
        except Exception as e:
            logger.error("Failed to save bulk page summary", domain=domain, error=str(e))
            raise
    
    async def get_all_bulk_domains(self, sort_by: str = 'created_at', order: str = 'desc') -> List[BulkDomainAnalysis]:
        """
        Get all bulk domain analysis records with sorting
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            # Validate sort_by field
            valid_sort_fields = ['created_at', 'domain_name', 'updated_at']
            if sort_by not in valid_sort_fields:
                sort_by = 'created_at'
            
            # Validate order
            if order not in ['asc', 'desc']:
                order = 'desc'
            
            query = self.client.table('bulk_domain_analysis').select('*')
            
            # Apply sorting
            if order == 'desc':
                query = query.order(sort_by, desc=True)
            else:
                query = query.order(sort_by, desc=False)
            
            result = query.execute()
            
            records = []
            if result.data:
                for row in result.data:
                    # Parse backlinks_bulk_page_summary if present
                    summary = None
                    if row.get('backlinks_bulk_page_summary'):
                        try:
                            from models.domain_analysis import BulkPageSummaryResult
                            summary = BulkPageSummaryResult(**row['backlinks_bulk_page_summary'])
                        except Exception as e:
                            logger.warning("Failed to parse summary data", domain=row.get('domain_name'), error=str(e))
                    
                    record = BulkDomainAnalysis(
                        id=row['id'],
                        domain_name=row['domain_name'],
                        provider=row.get('provider'),
                        backlinks_bulk_page_summary=summary,
                        created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')) if row.get('created_at') else None,
                        updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00')) if row.get('updated_at') else None
                    )
                    records.append(record)
            
            logger.info("Retrieved bulk domains", count=len(records), sort_by=sort_by, order=order)
            return records
            
        except Exception as e:
            logger.error("Failed to get all bulk domains", error=str(e))
            raise
    
    # Namecheap Domain Methods
    async def truncate_namecheap_domains(self) -> bool:
        """
        Clear all records from namecheap_domains table
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            logger.info("Starting table truncate")
            # Use a more efficient delete - delete all records
            # Supabase doesn't have TRUNCATE in the client, so we delete all
            result = self.client.table('namecheap_domains').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            logger.info("Table truncate complete", deleted_count=len(result.data) if result.data else 0)
            return True
            
        except Exception as e:
            logger.error("Failed to truncate namecheap_domains", error=str(e))
            # If delete fails, try alternative approach
            try:
                logger.info("Trying alternative truncate method")
                # Get all IDs and delete them
                all_records = self.client.table('namecheap_domains').select('id').execute()
                if all_records.data:
                    ids = [r['id'] for r in all_records.data]
                    for id in ids:
                        self.client.table('namecheap_domains').delete().eq('id', id).execute()
                logger.info("Alternative truncate complete")
                return True
            except Exception as e2:
                logger.error("Alternative truncate also failed", error=str(e2))
                raise
    
    async def load_namecheap_domains(self, domains: List[NamecheapDomain]) -> Dict[str, int]:
        """
        Bulk insert Namecheap domains using batch inserts for better performance
        Returns counts: inserted, skipped (duplicates)
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            if not domains:
                return {"inserted": 0, "skipped": 0, "total": 0}
            
            # Prepare all domain data for batch insert
            batch_size = 500  # Reduced batch size to avoid timeouts
            inserted_count = 0
            skipped_count = 0
            total_batches = (len(domains) + batch_size - 1) // batch_size
            
            logger.info("Starting bulk insert", total_domains=len(domains), batch_size=batch_size, total_batches=total_batches)
            
            # Process in batches
            for batch_num, i in enumerate(range(0, len(domains), batch_size), 1):
                batch = domains[i:i + batch_size]
                batch_data = []
                
                logger.info("Preparing batch", batch_num=batch_num, total_batches=total_batches, batch_size=len(batch))
                
                for domain in batch:
                    domain_data = {
                        'url': domain.url,
                        'name': domain.name,
                        'start_date': domain.start_date.isoformat() if domain.start_date else None,
                        'end_date': domain.end_date.isoformat() if domain.end_date else None,
                        'price': domain.price,
                        'start_price': domain.start_price,
                        'renew_price': domain.renew_price,
                        'bid_count': domain.bid_count,
                        'ahrefs_domain_rating': domain.ahrefs_domain_rating,
                        'umbrella_ranking': domain.umbrella_ranking,
                        'cloudflare_ranking': domain.cloudflare_ranking,
                        'estibot_value': domain.estibot_value,
                        'extensions_taken': domain.extensions_taken,
                        'keyword_search_count': domain.keyword_search_count,
                        'registered_date': domain.registered_date.isoformat() if domain.registered_date else None,
                        'last_sold_price': domain.last_sold_price,
                        'last_sold_year': domain.last_sold_year,
                        'is_partner_sale': domain.is_partner_sale,
                        'semrush_a_score': domain.semrush_a_score,
                        'majestic_citation': domain.majestic_citation,
                        'ahrefs_backlinks': domain.ahrefs_backlinks,
                        'semrush_backlinks': domain.semrush_backlinks,
                        'majestic_backlinks': domain.majestic_backlinks,
                        'majestic_trust_flow': domain.majestic_trust_flow,
                        'go_value': domain.go_value
                    }
                    batch_data.append(domain_data)
                
                try:
                    # Batch insert
                    logger.info("Inserting batch", batch_num=batch_num, records=len(batch_data))
                    result = self.client.table('namecheap_domains').insert(batch_data).execute()
                    inserted_count += len(batch_data)
                    logger.info("Batch inserted successfully", batch_num=batch_num, inserted=len(batch_data), total_inserted=inserted_count)
                    
                except Exception as e:
                    # If batch insert fails (e.g., due to duplicates), fall back to individual inserts
                    logger.warning("Batch insert failed, falling back to individual inserts", 
                                 batch_num=batch_num, error=str(e), batch_start=i)
                    for idx, domain_data in enumerate(batch_data):
                        try:
                            self.client.table('namecheap_domains').insert(domain_data).execute()
                            inserted_count += 1
                            if (idx + 1) % 100 == 0:
                                logger.info("Individual insert progress", batch_num=batch_num, processed=idx+1, total=len(batch_data))
                        except Exception as e2:
                            if 'duplicate' in str(e2).lower() or 'unique' in str(e2).lower():
                                skipped_count += 1
                            else:
                                logger.warning("Failed to insert domain", domain=domain_data.get('name'), error=str(e2))
                                skipped_count += 1
            
            logger.info("Bulk insert complete", inserted=inserted_count, skipped=skipped_count, total=len(domains))
            return {
                "inserted": inserted_count,
                "skipped": skipped_count,
                "total": len(domains)
            }
            
        except Exception as e:
            logger.error("Failed to load namecheap domains", error=str(e), exc_info=True)
            raise
    
    async def get_all_namecheap_domains(
        self, 
        sort_by: str = 'name', 
        order: str = 'asc', 
        search: str = None,
        extensions: List[str] = None,
        no_special_chars: bool = None,
        no_numbers: bool = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[NamecheapDomain]:
        """
        Get all Namecheap domains with optional search, sorting, and filtering
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            # Validate sort_by field - expanded list
            valid_sort_fields = [
                'name', 'price', 'end_date', 'ahrefs_domain_rating', 'estibot_value', 
                'bid_count', 'created_at', 'keyword_search_count', 'last_sold_year',
                'is_partner_sale', 'semrush_a_score', 'ahrefs_backlinks', 
                'semrush_backlinks', 'majestic_trust_flow', 'go_value'
            ]
            if sort_by not in valid_sort_fields:
                sort_by = 'name'
            
            # Validate order
            if order not in ['asc', 'desc']:
                order = 'asc'
            
            query = self.client.table('namecheap_domains').select('*')
            
            # Apply search filter
            if search:
                query = query.ilike('name', f'%{search}%')
            
            # Apply extension filter at database level using SQL pattern matching
            if extensions:
                # Build OR conditions for each extension
                # Use SQL LIKE pattern: name LIKE '%.com' OR name LIKE '%.net' etc.
                extension_filters = []
                for ext in extensions:
                    # Remove leading dot if present for pattern matching
                    ext_clean = ext.lstrip('.')
                    extension_filters.append(f"name.like.%.{ext_clean}")
                
                # Apply first extension filter, then chain OR conditions
                if extension_filters:
                    # Supabase doesn't support OR directly in Python client easily
                    # So we'll filter in Python but fetch a reasonable limit first
                    pass  # Will filter in Python after fetch
            
            # Apply sorting
            if order == 'desc':
                query = query.order(sort_by, desc=True)
            else:
                query = query.order(sort_by, desc=False)
            
            # Apply pagination FIRST to limit what we fetch from database
            # For filtered queries, fetch more records since filtering happens in Python
            # Cap fetch size to prevent database timeouts
            MAX_FETCH = 1000  # Maximum records to fetch in one query
            
            if extensions or no_special_chars or no_numbers:
                # When filtering, fetch more to get enough results after filtering
                fetch_limit = min(limit * 3, MAX_FETCH)
            else:
                fetch_limit = min(limit, MAX_FETCH)
            
            query = query.range(offset, offset + fetch_limit - 1)
            
            result = query.execute()
            
            records = []
            if result.data:
                for row in result.data:
                    domain_name = row.get('name', '')
                    
                    # Apply extension filter
                    if extensions:
                        # Extract extension (e.g., 'example.com' -> '.com')
                        if '.' in domain_name:
                            domain_ext = '.' + domain_name.split('.')[-1]
                            if domain_ext not in extensions:
                                continue
                        else:
                            # No extension found, skip if extensions filter is set
                            continue
                    
                    # Apply no special characters filter
                    if no_special_chars:
                        # Check if domain has special characters (excluding dots and hyphens which are valid)
                        # Special chars: anything that's not alphanumeric, dot, or hyphen
                        if re.search(r'[^a-zA-Z0-9.\-]', domain_name):
                            continue
                    
                    # Apply no numbers filter
                    if no_numbers:
                        # Check if domain has any digits
                        if re.search(r'\d', domain_name):
                            continue
                    
                    # Stop if we've collected enough records after filtering
                    if len(records) >= limit:
                        break
                    domain = NamecheapDomain(
                        id=row['id'],
                        url=row.get('url'),
                        name=row['name'],
                        start_date=datetime.fromisoformat(row['start_date'].replace('Z', '+00:00')) if row.get('start_date') else None,
                        end_date=datetime.fromisoformat(row['end_date'].replace('Z', '+00:00')) if row.get('end_date') else None,
                        price=float(row['price']) if row.get('price') is not None else None,
                        start_price=float(row['start_price']) if row.get('start_price') is not None else None,
                        renew_price=float(row['renew_price']) if row.get('renew_price') is not None else None,
                        bid_count=row.get('bid_count'),
                        ahrefs_domain_rating=float(row['ahrefs_domain_rating']) if row.get('ahrefs_domain_rating') is not None else None,
                        umbrella_ranking=row.get('umbrella_ranking'),
                        cloudflare_ranking=row.get('cloudflare_ranking'),
                        estibot_value=float(row['estibot_value']) if row.get('estibot_value') is not None else None,
                        extensions_taken=row.get('extensions_taken'),
                        keyword_search_count=row.get('keyword_search_count'),
                        registered_date=datetime.fromisoformat(row['registered_date'].replace('Z', '+00:00')) if row.get('registered_date') else None,
                        last_sold_price=float(row['last_sold_price']) if row.get('last_sold_price') is not None else None,
                        last_sold_year=row.get('last_sold_year'),
                        is_partner_sale=row.get('is_partner_sale'),
                        semrush_a_score=row.get('semrush_a_score'),
                        majestic_citation=row.get('majestic_citation'),
                        ahrefs_backlinks=row.get('ahrefs_backlinks'),
                        semrush_backlinks=row.get('semrush_backlinks'),
                        majestic_backlinks=row.get('majestic_backlinks'),
                        majestic_trust_flow=float(row['majestic_trust_flow']) if row.get('majestic_trust_flow') is not None else None,
                        go_value=float(row['go_value']) if row.get('go_value') is not None else None,
                        created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')) if row.get('created_at') else None,
                        updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00')) if row.get('updated_at') else None
                    )
                    records.append(domain)
            
            logger.info("Retrieved namecheap domains", count=len(records), sort_by=sort_by, order=order, search=search)
            return records
            
        except Exception as e:
            logger.error("Failed to get namecheap domains", error=str(e))
            raise
    
    async def get_namecheap_domain_by_name(self, domain_name: str) -> Optional[NamecheapDomain]:
        """
        Get single Namecheap domain by name field
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            result = self.client.table('namecheap_domains').select('*').eq('name', domain_name).execute()
            
            if not result.data or len(result.data) == 0:
                return None
            
            row = result.data[0]
            domain = NamecheapDomain(
                id=row['id'],
                url=row.get('url'),
                name=row['name'],
                start_date=datetime.fromisoformat(row['start_date'].replace('Z', '+00:00')) if row.get('start_date') else None,
                end_date=datetime.fromisoformat(row['end_date'].replace('Z', '+00:00')) if row.get('end_date') else None,
                price=float(row['price']) if row.get('price') is not None else None,
                start_price=float(row['start_price']) if row.get('start_price') is not None else None,
                renew_price=float(row['renew_price']) if row.get('renew_price') is not None else None,
                bid_count=row.get('bid_count'),
                ahrefs_domain_rating=float(row['ahrefs_domain_rating']) if row.get('ahrefs_domain_rating') is not None else None,
                umbrella_ranking=row.get('umbrella_ranking'),
                cloudflare_ranking=row.get('cloudflare_ranking'),
                estibot_value=float(row['estibot_value']) if row.get('estibot_value') is not None else None,
                extensions_taken=row.get('extensions_taken'),
                keyword_search_count=row.get('keyword_search_count'),
                registered_date=datetime.fromisoformat(row['registered_date'].replace('Z', '+00:00')) if row.get('registered_date') else None,
                last_sold_price=float(row['last_sold_price']) if row.get('last_sold_price') is not None else None,
                last_sold_year=row.get('last_sold_year'),
                is_partner_sale=row.get('is_partner_sale'),
                semrush_a_score=row.get('semrush_a_score'),
                majestic_citation=row.get('majestic_citation'),
                ahrefs_backlinks=row.get('ahrefs_backlinks'),
                semrush_backlinks=row.get('semrush_backlinks'),
                majestic_backlinks=row.get('majestic_backlinks'),
                majestic_trust_flow=float(row['majestic_trust_flow']) if row.get('majestic_trust_flow') is not None else None,
                go_value=float(row['go_value']) if row.get('go_value') is not None else None,
                created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')) if row.get('created_at') else None,
                updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00')) if row.get('updated_at') else None
            )
            
            return domain
            
        except Exception as e:
            logger.error("Failed to get namecheap domain by name", domain=domain_name, error=str(e))
            raise
    
    async def get_bulk_domain(self, domain_name: str) -> Optional[BulkDomainAnalysis]:
        """
        Get bulk domain analysis record by domain name
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            result = self.client.table('bulk_domain_analysis').select('*').eq('domain_name', domain_name).execute()
            
            if not result.data or len(result.data) == 0:
                return None
            
            row = result.data[0]
            
            # Parse backlinks_bulk_page_summary if present
            summary = None
            if row.get('backlinks_bulk_page_summary'):
                try:
                    from models.domain_analysis import BulkPageSummaryResult
                    summary = BulkPageSummaryResult(**row['backlinks_bulk_page_summary'])
                except Exception as e:
                    logger.warning("Failed to parse summary data", domain=domain_name, error=str(e))
            
            record = BulkDomainAnalysis(
                id=row['id'],
                domain_name=row['domain_name'],
                provider=row.get('provider'),
                backlinks_bulk_page_summary=summary,
                created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')) if row.get('created_at') else None,
                updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00')) if row.get('updated_at') else None
            )
            
            return record
            
        except Exception as e:
            logger.error("Failed to get bulk domain", domain=domain_name, error=str(e))
            raise
    
    # Auctions Methods
    async def truncate_auctions(self) -> bool:
        """Truncate auctions table - skip if empty, otherwise use efficient deletion"""
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            # First, check if table is empty or small
            count_result = self.client.table('auctions').select('id', count='exact').limit(1).execute()
            total_count = count_result.count if hasattr(count_result, 'count') else None
            
            if total_count is not None and total_count == 0:
                logger.info("Auctions table is already empty, skipping truncation")
                return True
            
            logger.info("Truncating auctions table", total_records=total_count)
            
            # For very large tables, try N8N workflow first (executes SQL directly - fastest)
            if total_count and total_count > 100000:
                try:
                    from services.n8n_service import N8NService
                    n8n_service = N8NService()
                    # Check if truncate webhook URL is configured
                    truncate_url = getattr(self.settings, 'N8N_WEBHOOK_URL_TRUNCATE', None)
                    if n8n_service.enabled and truncate_url:
                        logger.info("Attempting truncate via N8N workflow", webhook_url=truncate_url)
                        result = await n8n_service.trigger_truncate_auctions_workflow()
                        if result:
                            logger.info("Truncate triggered via N8N workflow", request_id=result.get('request_id'))
                            # Wait for N8N to complete (SQL truncate is fast, but give it time)
                            import asyncio
                            await asyncio.sleep(5)  # Give N8N time to execute SQL
                            # Verify truncation completed
                            for attempt in range(3):  # Check up to 3 times
                                verify_result = self.client.table('auctions').select('id', count='exact').limit(1).execute()
                                if verify_result.count == 0:
                                    logger.info("Auctions table truncated successfully via N8N")
                                    return True
                                elif attempt < 2:
                                    await asyncio.sleep(2)  # Wait a bit more
                                    continue
                                else:
                                    logger.warning("N8N truncate may not have completed, table still has records", remaining=verify_result.count)
                        else:
                            logger.warning("N8N truncate workflow trigger returned None")
                    else:
                        logger.info("N8N truncate not configured", enabled=n8n_service.enabled, truncate_url=bool(truncate_url))
                except Exception as n8n_error:
                    logger.warning("N8N truncate failed", error=str(n8n_error))
            
            # For very large tables, skip truncation and use upsert instead
            # This is much faster than trying to delete 867k+ records
            if total_count and total_count > 100000:
                logger.info("Skipping truncation for large table - will use upsert to handle duplicates", 
                           total_records=total_count)
                return True
            
            # For smaller tables, use simple DELETE
            try:
                # Delete all records using a simple filter
                self.client.table('auctions').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                logger.info("Auctions table truncated using DELETE")
                return True
            except Exception as delete_error:
                logger.warning("DELETE truncation failed", error=str(delete_error))
                # If DELETE fails, skip truncation - upsert will handle it
                logger.info("Skipping truncation - will use upsert on upload")
                return True
            
        except Exception as e:
            logger.error("Failed to truncate auctions", error=str(e))
            raise
    
    async def bulk_insert_auctions(self, auctions: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Bulk upsert auctions using batch inserts
        Updates existing records, adds new ones, preserves backlinks_bulk_page_summary (in bulk_domain_analysis)
        
        Args:
            auctions: List of auction dictionaries ready for database insertion
            
        Returns:
            Dict with inserted, updated, skipped, total counts
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            if not auctions:
                return {"inserted": 0, "updated": 0, "skipped": 0, "total": 0}
            
            batch_size = 500
            inserted_count = 0
            updated_count = 0
            skipped_count = 0
            total_batches = (len(auctions) + batch_size - 1) // batch_size
            
            logger.info("Starting bulk upsert auctions", total=len(auctions), batch_size=batch_size, total_batches=total_batches)
            
            # Process in batches - upsert handles both inserts and updates
            # Note: We can't easily distinguish inserts from updates without pre-checking,
            # which is expensive for large files. We'll approximate by assuming all are inserts
            # and let the database handle the upsert logic.
            for batch_num, i in enumerate(range(0, len(auctions), batch_size), 1):
                batch = auctions[i:i + batch_size]
                
                try:
                    # Use upsert to handle duplicates based on unique constraint
                    # The unique constraint is on (domain, auction_site, expiration_date)
                    # Note: backlinks_bulk_page_summary is in bulk_domain_analysis table, not auctions
                    # So it's automatically preserved when we update auctions
                    result = self.client.table('auctions').upsert(
                        batch,
                        on_conflict='domain,auction_site,expiration_date'
                    ).execute()
                    
                    # Approximate: assume all are inserts (upsert will update if exists)
                    # For accurate counts, we'd need to check each record first, which is expensive
                    inserted_count += len(batch)
                    
                    if batch_num % 10 == 0:
                        logger.info("Batch upsert progress", 
                                   batch_num=batch_num, 
                                   total_batches=total_batches, 
                                   processed=inserted_count)
                    
                except Exception as e:
                    # Fall back to individual upserts on batch failure
                    logger.warning("Batch upsert failed, using individual upserts", batch_num=batch_num, error=str(e))
                    for auction_data in batch:
                        try:
                            self.client.table('auctions').upsert(
                                auction_data,
                                on_conflict='domain,auction_site,expiration_date'
                            ).execute()
                            inserted_count += 1
                        except Exception as e2:
                            if 'duplicate' in str(e2).lower() or 'unique' in str(e2).lower():
                                skipped_count += 1
                            else:
                                logger.warning("Failed to upsert auction", domain=auction_data.get('domain'), error=str(e2))
                                skipped_count += 1
            
            logger.info("Bulk upsert auctions complete", 
                       processed=inserted_count,
                       skipped=skipped_count, 
                       total=len(auctions))
            # Note: We can't easily distinguish inserts from updates without expensive pre-checks
            # Return processed count (which includes both inserts and updates)
            return {
                "inserted": inserted_count,  # Actually processed (inserts + updates)
                "updated": 0,  # Not tracked separately for performance
                "skipped": skipped_count,
                "total": len(auctions)
            }
            
        except Exception as e:
            logger.error("Failed to bulk insert auctions", error=str(e))
            raise
    
    async def delete_expired_auctions(self) -> int:
        """
        Delete auctions with expiration_date in the past
        
        Returns:
            Number of records deleted
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            # Call the optimized RPC function which deletes in chunks (limit 10k)
            result = self.client.rpc('delete_expired_auctions', {}).execute()
            
            # Verify result format (RPC returns integer directly or in data)
            deleted_count = result.data if result.data is not None else 0
            
            logger.info("Deleted expired auctions", count=deleted_count)
            return deleted_count
            
        except Exception as e:
            logger.error("Failed to delete expired auctions", error=str(e))
            # Don't raise error to prevent breaking the calling process
            return 0
            
        except Exception as e:
            logger.error("Failed to delete expired auctions", error=str(e))
            # Don't raise - deletion of expired records is not critical
            # Return 0 to indicate no records were deleted
            return 0
    
    async def get_preferred_auctions_without_stats(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get preferred auctions without statistics, ordered by expiration_date ASC
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of auction dictionaries
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            result = (
                self.client.table('auctions')
                .select('*')
                .eq('preferred', True)
                .eq('has_statistics', False)
                .order('expiration_date', desc=False)
                .limit(limit)
                .execute()
            )
            
            auctions = result.data if result.data else []
            logger.info("Fetched preferred auctions without stats", count=len(auctions), limit=limit)
            return auctions
            
        except Exception as e:
            logger.error("Failed to get preferred auctions without stats", error=str(e))
            raise
    
    async def mark_has_statistics(self, domain_names: List[str]) -> int:
        """
        Mark auctions as having statistics
        
        Args:
            domain_names: List of domain names to update
            
        Returns:
            Number of records updated
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            if not domain_names:
                return 0
            
            updated_count = 0
            batch_size = 100
            
            for i in range(0, len(domain_names), batch_size):
                batch = domain_names[i:i + batch_size]
                
                for domain_name in batch:
                    try:
                        self.client.table('auctions').update({
                            'has_statistics': True,
                            'updated_at': datetime.utcnow().isoformat()
                        }).eq('domain', domain_name).execute()
                        updated_count += 1
                    except Exception as e:
                        logger.warning("Failed to mark has_statistics", domain=domain_name, error=str(e))
                        continue
            
            logger.info("Marked auctions with statistics", updated=updated_count, total=len(domain_names))
            return updated_count
            
        except Exception as e:
            logger.error("Failed to mark has_statistics", error=str(e))
            raise
    
    async def get_auctions_with_statistics(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = 'expiration_date',
        order: str = 'asc',
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get auctions with joined statistics from bulk_domain_analysis
        
        Args:
            filters: Dict with optional filters (preferred, auction_site, etc.)
            sort_by: Field to sort by
            order: Sort order ('asc' or 'desc')
            limit: Maximum number of records
            offset: Number of records to skip
            
        Returns:
            Dict with auctions list and total count
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            # Build query
            query = self.client.table('auctions').select('*')
            
            # Apply filters
            if filters:
                if filters.get('preferred') is not None:
                    query = query.eq('preferred', filters['preferred'])
                if filters.get('auction_site'):
                    query = query.eq('auction_site', filters['auction_site'])
                if filters.get('auction_sites'):
                    # Filter by multiple auction sites
                    sites = filters['auction_sites']
                    if isinstance(sites, list) and len(sites) > 0:
                        query = query.in_('auction_site', sites)
                if filters.get('tld'):
                    # Filter by TLD: domain should end with the specified TLD
                    # TLD comes in format like ".com" or "com", handle both
                    tld = filters['tld']
                    if not tld.startswith('.'):
                        tld = '.' + tld
                    # Use PostgreSQL's ILIKE operator (case-insensitive) to match domains ending with the TLD
                    # PostgREST supports ilike filter
                    query = query.ilike('domain', f'%{tld}')
                if filters.get('tlds'):
                    # Filter by multiple TLDs: domain should end with any of the specified TLDs
                    # TLDs come as a list like [".com", ".io", ".ai"]
                    tlds = filters['tlds']
                    if isinstance(tlds, list) and len(tlds) > 0:
                        # Normalize TLDs (ensure they start with .)
                        normalized_tlds = [tld if tld.startswith('.') else f'.{tld}' for tld in tlds if tld]
                        # Use OR condition for multiple TLDs - PostgREST doesn't support OR directly,
                        # so we'll use a workaround with multiple ilike filters
                        # For now, we'll filter by the first TLD and let the frontend handle multiple
                        # TODO: Implement proper OR filtering for multiple TLDs
                        if normalized_tlds:
                            query = query.ilike('domain', f'%{normalized_tlds[0]}')
                if filters.get('offering_type'):
                    query = query.eq('offer_type', filters['offering_type'])
                if filters.get('expiration_from_date'):
                    # Filter by expiration date from (greater than or equal)
                    query = query.gte('expiration_date', filters['expiration_from_date'])
                if filters.get('expiration_to_date'):
                    # Filter by expiration date to (less than or equal)
                    # If date is provided without time (YYYY-MM-DD), append time to include the full day
                    exp_to = filters['expiration_to_date']
                    if isinstance(exp_to, str) and len(exp_to) == 10:  # Simple check for YYYY-MM-DD
                        exp_to = f"{exp_to}T23:59:59"
                    query = query.lte('expiration_date', exp_to)
                
                # Default: only show auctions that haven't expired yet
                if not filters.get('expiration_from_date'):
                    # Use current UTC time
                    now = datetime.now(timezone.utc).isoformat()
                    query = query.gte('expiration_date', now)
                if filters.get('has_statistics') is not None:
                    query = query.eq('has_statistics', filters['has_statistics'])
                if filters.get('scored') is not None:
                    if filters['scored']:
                        query = query.not_.is_('score', 'null')
                    else:
                        query = query.is_('score', 'null')
                if filters.get('min_rank') is not None:
                    query = query.gte('ranking', filters['min_rank'])
                if filters.get('max_rank') is not None:
                    query = query.lte('ranking', filters['max_rank'])
                if filters.get('min_score') is not None:
                    query = query.gte('score', filters['min_score'])
                if filters.get('max_score') is not None:
                    query = query.lte('score', filters['max_score'])
            
            # Apply sorting
            valid_sort_fields = ['expiration_date', 'score', 'ranking', 'created_at', 'domain', 'backlinks', 'referring_domains', 'backlinks_spam_score', 'domain_rating', 'organic_traffic']
            if sort_by not in valid_sort_fields:
                sort_by = 'expiration_date'
            
            if order == 'desc':
                query = query.order(sort_by, desc=True, nullsfirst=False) # python client uses nullsfirst=False for NULLS LAST
            else:
                query = query.order(sort_by, desc=False)
            
            # Get total count - execute query with count header
            # Note: We'll estimate total count by getting a sample and extrapolating
            # For exact count, we'd need a separate count query, but Supabase client doesn't support it directly
            # So we'll get the paginated results and use a reasonable estimate
            result = query.range(offset, offset + limit - 1).execute()
            auctions = result.data if result.data else []
            
            # Estimate total count - if we got a full page, there might be more
            # This is an approximation, but for large datasets it's acceptable
            if len(auctions) == limit:
                # We got a full page, so there are likely more records
                # Estimate: at least (offset + limit) records, possibly many more
                total_count = offset + limit + (1000 if len(auctions) == limit else 0)  # Conservative estimate
            else:
                # We got less than a full page, so this is likely the total
                total_count = offset + len(auctions)
            
            # Return auctions directly (bulk_domain_analysis table is no longer used)
            # Statistics are now stored directly in the auctions table's page_statistics field
            report_items = []
            for auction in auctions:
                report_item = {
                    **auction,
                    'statistics': auction.get('page_statistics')  # Get statistics from auctions table if available
                }
                report_items.append(report_item)
            
            # For better accuracy, check if there are more records
            has_more = len(auctions) == limit
            
            logger.info("Fetched auctions with statistics", count=len(report_items), total_estimate=total_count, offset=offset, has_more=has_more)
            
            return {
                "auctions": report_items,
                "total_count": total_count,
                "count": len(report_items),
                "has_more": has_more
            }
            
        except Exception as e:
            logger.error("Failed to get auctions with statistics", error=str(e))
            raise
    
    async def get_auctions_missing_any_metric_with_filters(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = 'expiration_date',
        sort_order: str = 'asc',
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get auctions matching filters that are missing ANY of the four DataForSEO metrics
        
        Args:
            filters: Dict with optional filters
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            limit: Maximum number of records to return
            
        Returns:
            List of auction dictionaries
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            # Build query
            query = self.client.table('auctions').select('*')
            
            # Apply filters (Reuse logic from get_auctions_with_statistics)
            if filters:
                if filters.get('preferred') is not None:
                    query = query.eq('preferred', filters['preferred'])
                if filters.get('auction_site'):
                    query = query.eq('auction_site', filters['auction_site'])
                if filters.get('tld'):
                    tld = filters['tld']
                    if not tld.startswith('.'):
                        tld = '.' + tld
                    query = query.ilike('domain', f'%{tld}')
                if filters.get('tlds'):
                    tlds = filters['tlds']
                    if isinstance(tlds, list) and len(tlds) > 0:
                        normalized_tlds = [tld if tld.startswith('.') else f'.{tld}' for tld in tlds if tld]
                        # Use first TLD for now as simple filter
                        if normalized_tlds:
                            query = query.ilike('domain', f'%{normalized_tlds[0]}')
                if filters.get('offering_type'):
                    query = query.eq('offer_type', filters['offering_type'])
                if filters.get('expiration_from_date'):
                    query = query.gte('expiration_date', filters['expiration_from_date'])
                if filters.get('expiration_to_date'):
                    exp_to = filters['expiration_to_date']
                    if isinstance(exp_to, str) and len(exp_to) == 10:
                        exp_to = f"{exp_to}T23:59:59"
                    query = query.lte('expiration_date', exp_to)
                if filters.get('has_statistics') is not None:
                    query = query.eq('has_statistics', filters['has_statistics'])
                if filters.get('scored') is not None:
                    if filters['scored']:
                        query = query.not_.is_('score', 'null')
                    else:
                        query = query.is_('score', 'null')
                if filters.get('min_rank') is not None:
                    query = query.gte('ranking', filters['min_rank'])
                if filters.get('max_rank') is not None:
                    query = query.lte('ranking', filters['max_rank'])
                if filters.get('min_score') is not None:
                    query = query.gte('score', filters['min_score'])
                if filters.get('max_score') is not None:
                    query = query.lte('score', filters['max_score'])
            
            # Apply sorting
            valid_sort_fields = ['expiration_date', 'score', 'ranking', 'created_at', 'domain', 'backlinks', 'referring_domains', 'backlinks_spam_score']
            if sort_by not in valid_sort_fields:
                sort_by = 'expiration_date'
            
            if sort_order == 'desc':
                query = query.order(sort_by, desc=True)
            else:
                query = query.order(sort_by, desc=False)
            
            # Fetch candidates - fetch more than limit to allow regarding in-memory filtering
            fetch_limit = limit * 2
            result = query.limit(fetch_limit).execute()
            candidates = result.data if result.data else []
            
            # Filter in-memory for missing metrics
            # We look for MISSING traffic, rank, backlinks, OR spam_score in page_statistics
            missing_metrics_auctions = []
            
            for auction in candidates:
                stats = auction.get('page_statistics') or {}
                
                # Check metrics
                # Note: keys depend on how they are stored. Assuming standard keys.
                has_traffic = 'traffic' in stats and stats['traffic'] is not None
                has_rank = 'rank' in stats and stats['rank'] is not None
                has_backlinks = 'backlinks' in stats and stats['backlinks'] is not None
                has_spam_score = 'spam_score' in stats and stats['spam_score'] is not None
                
                # If ANY is missing, include this auction
                if not (has_traffic and has_rank and has_backlinks and has_spam_score):
                    missing_metrics_auctions.append(auction)
                    if len(missing_metrics_auctions) >= limit:
                        break
            
            logger.info("Fetched auctions missing metrics", found=len(missing_metrics_auctions), examined=len(candidates))
            return missing_metrics_auctions

        except Exception as e:
            logger.error("Failed to get auctions missing metrics", error=str(e))
            raise
    
    async def update_auction_page_statistics(self, domain: str, page_statistics: Dict[str, Any]) -> bool:
        """
        Update page_statistics for an auction
        
        Args:
            domain: Domain name
            page_statistics: Statistics data to update
            
        Returns:
            True if updated, False if domain not found
        """
        try:
            if not self.client:
                self._initialize_client()
                
            # First fetch existing statistics to merge
            response = self.client.table('auctions').select('page_statistics').eq('domain', domain).execute()
            
            if not response.data or len(response.data) == 0:
                # logger.warning("Domain not found for statistics update", domain=domain)
                return False
                
            current_stats = response.data[0].get('page_statistics') or {}
            
            # Merge new stats into existing
            updated_stats = current_stats.copy()
            updated_stats.update(page_statistics)
            
            # Prepare update data with top-level columns for sorting
            update_data = {
                'page_statistics': updated_stats,
                'has_statistics': True,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Extract metrics to top-level columns if present
            # Rank
            if 'rank' in updated_stats and updated_stats['rank'] is not None:
                update_data['ranking'] = updated_stats['rank']
                
            # Backlinks
            if 'backlinks' in updated_stats and updated_stats['backlinks'] is not None:
                update_data['backlinks'] = updated_stats['backlinks']
                
            # Referring Domains
            if 'referring_domains' in updated_stats and updated_stats['referring_domains'] is not None:
                update_data['referring_domains'] = updated_stats['referring_domains']
                
            # Spam Score (map spam_score or backlinks_spam_score)
            spam_score = updated_stats.get('backlinks_spam_score') or updated_stats.get('spam_score')
            if spam_score is not None:
                update_data['backlinks_spam_score'] = spam_score
            
            # Domain Rating (DR)
            # Check for various common keys for DR, fallback to 'rank' as proxy for DR/Authority
            domain_rating = updated_stats.get('domain_rating') or updated_stats.get('dr') or updated_stats.get('rank')
            if domain_rating is not None:
                update_data['domain_rating'] = domain_rating
                
            # Organic Traffic
            # Check for various common keys for Traffic
            organic_traffic = updated_stats.get('organic_traffic') or updated_stats.get('etv') or updated_stats.get('traffic')
            if organic_traffic is not None:
                update_data['organic_traffic'] = organic_traffic

            # Update the record
            update_response = self.client.table('auctions').update(update_data).eq('domain', domain).execute()
            
            if update_response.data and len(update_response.data) > 0:
                return True
            return False
            
        except Exception as e:
            logger.error("Error updating auction page statistics", domain=domain, error=str(e))
            return False

    async def update_auction_traffic_data(self, domain: str, traffic_data: Dict[str, Any]) -> bool:
        """
        Update traffic data for an auction
        Aliased to update_auction_page_statistics to merge into the same JSONB column
        """
        return await self.update_auction_page_statistics(domain, traffic_data)

    async def get_unique_tlds(self) -> List[str]:
        """
        Get all unique TLDs from the auctions table
        
        Returns:
            List of unique TLDs (e.g., ['.com', '.ai', '.net'])
        """
        try:
            # Fetch all domains and extract TLDs
            result = (
                self.client.table('auctions')
                .select('domain')
                .execute()
            )
            
            tlds = set()
            for auction in result.data if result.data else []:
                domain = auction.get('domain', '')
                if '.' in domain:
                    # Extract TLD (last part after last dot)
                    parts = domain.rsplit('.', 1)
                    if len(parts) == 2:
                        tld = '.' + parts[1].lower()
                        tlds.add(tld)
            
            return sorted(list(tlds))
        except Exception as e:
            logger.error("Failed to get unique TLDs", error=str(e), exc_info=True)
            return []
    
    async def upload_csv_to_storage(self, file_content: bytes, filename: str, bucket: str = "auction-csvs") -> str:
        """
        Upload CSV file to Supabase storage
        
        Args:
            file_content: File content as bytes
            filename: Name for the file in storage
            bucket: Storage bucket name (default: auction-csvs)
            
        Returns:
            File path in storage (relative to bucket)
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            file_size = len(file_content)
            file_size_mb = file_size / (1024 * 1024)
            
            logger.info("Starting storage upload", 
                       bucket=bucket, 
                       filename=filename, 
                       size_bytes=file_size,
                       size_mb=round(file_size_mb, 2))
            
            # Upload to storage with timeout handling
            # Supabase storage upload accepts bytes directly, not BytesIO
            try:
                storage_response = self.client.storage.from_(bucket).upload(
                    path=filename,
                    file=file_content,  # Pass bytes directly, not BytesIO
                    file_options={
                        "content-type": "text/csv", 
                        "upsert": "true",
                        "cache-control": "3600"
                    }
                )
                
                logger.info("Uploaded CSV to storage successfully", 
                           bucket=bucket, 
                           filename=filename,
                           size_mb=round(file_size_mb, 2))
                return filename
                
            except Exception as upload_error:
                # Check if it's a timeout or size-related error
                error_str = str(upload_error).lower()
                if "timeout" in error_str or "timed out" in error_str:
                    logger.error("Storage upload timed out", 
                               bucket=bucket, 
                               filename=filename,
                               size_mb=round(file_size_mb, 2),
                               error=str(upload_error))
                    raise Exception(f"Upload timed out for file {filename} ({round(file_size_mb, 2)}MB). The file may be too large.")
                elif "size" in error_str or "too large" in error_str:
                    logger.error("File too large for storage", 
                               bucket=bucket, 
                               filename=filename,
                               size_mb=round(file_size_mb, 2),
                               error=str(upload_error))
                    raise Exception(f"File {filename} ({round(file_size_mb, 2)}MB) is too large for storage upload.")
                else:
                    raise
            
        except Exception as e:
            logger.error("Failed to upload CSV to storage", 
                        bucket=bucket, 
                        filename=filename, 
                        error=str(e),
                        error_type=type(e).__name__)
            raise
    
    async def download_from_storage(self, bucket: str, path: str) -> bytes:
        """
        Download file from Supabase storage
        
        Args:
            bucket: Storage bucket name
            path: File path in storage (relative to bucket)
            
        Returns:
            File content as bytes
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            import httpx
            
            # Construct the Storage API URL
            # Supabase Storage API: /storage/v1/object/{bucket}/{path}
            storage_url = f"{self.settings.SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
            
            # Get service role key for authentication
            service_role_key = self.settings.SUPABASE_SERVICE_ROLE_KEY or self.settings.SUPABASE_KEY
            
            logger.info("Downloading file from storage", 
                       bucket=bucket, 
                       path=path,
                       url=storage_url)
            
            # Use httpx.AsyncClient for async download
            async with httpx.AsyncClient(timeout=300.0, verify=bool(getattr(self.settings, 'SUPABASE_VERIFY_SSL', True))) as client:
                response = await client.get(
                    storage_url,
                    headers={
                        "Authorization": f"Bearer {service_role_key}",
                        "apikey": service_role_key
                    }
                )
                
                if response.status_code == 404:
                    raise Exception(f"File not found in storage: bucket={bucket}, path={path}")
                
                response.raise_for_status()
                
                file_size = len(response.content)
                file_size_mb = file_size / (1024 * 1024)
                
                logger.info("Downloaded file from storage successfully", 
                           bucket=bucket, 
                           path=path,
                           size_bytes=file_size,
                           size_mb=round(file_size_mb, 2))
                
                return response.content
                
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code} error downloading from storage: {e.response.text}"
            logger.error("Failed to download from storage (HTTP error)", 
                        bucket=bucket, 
                        path=path,
                        status_code=e.response.status_code,
                        error=error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error("Failed to download from storage", 
                        bucket=bucket, 
                        path=path,
                        error=str(e),
                        error_type=type(e).__name__)
            raise

    async def download_to_file(self, bucket: str, path: str, target_path: str, max_retries: int = 3) -> int:
        """
        Download file from Supabase storage into a local file using streaming and retries
        
        Args:
            bucket: Storage bucket name
            path: File path in storage
            target_path: Local path to save the file
            max_retries: Maximum number of retry attempts
            
        Returns:
            Total bytes downloaded
        """
        import httpx
        import asyncio
        import time
        from pathlib import Path
        
        base_url = self.settings.SUPABASE_URL.rstrip('/')
        bucket_clean = bucket.strip('/')
        path_clean = path.lstrip('/')
        storage_url = f"{base_url}/storage/v1/object/{bucket_clean}/{path_clean}"
        
        service_role_key = self.settings.SUPABASE_SERVICE_ROLE_KEY or self.settings.SUPABASE_KEY
        
        headers = {
            "Authorization": f"Bearer {service_role_key}",
            "apikey": service_role_key
        }
        
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt
                    logger.info("Retrying storage download", attempt=attempt, wait_time=wait_time, bucket=bucket, path=path)
                    await asyncio.sleep(wait_time)
                
                async with httpx.AsyncClient(timeout=600.0, verify=bool(getattr(self.settings, 'SUPABASE_VERIFY_SSL', True))) as client:
                    async with client.stream("GET", storage_url, headers=headers) as response:
                        if response.status_code == 404:
                            raise Exception(f"File not found in storage: bucket={bucket}, path={path}")
                        
                        response.raise_for_status()
                        
                        total_bytes = 0
                        with open(target_path, 'wb') as f:
                            async for chunk in response.aiter_bytes(chunk_size=8192):
                                f.write(chunk)
                                total_bytes += len(chunk)
                        
                        if total_bytes == 0:
                            logger.warning("Downloaded 0 bytes from storage", bucket=bucket, path=path)
                            # We don't raise here strictly in case empty files are valid, but for CSVs usually not.
                            # But let the parser handle empty files to distinguish between "download failed" and "file is empty".
                        
                        logger.info("Downloaded file to disk successfully", 
                                   bucket=bucket, 
                                   path=path, 
                                   local_path=target_path,
                                   size_mb=round(total_bytes / (1024 * 1024), 2))
                        return total_bytes
            
            except (httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                last_error = e
                logger.warning("Transient error during storage download", attempt=attempt, error=str(e))
                continue
            except Exception as e:
                logger.error("Terminal error during storage download", bucket=bucket, path=path, error=str(e))
                raise
        
        raise Exception(f"Failed to download from storage after {max_retries} retries: {str(last_error)}")
    
    async def create_csv_upload_job(
        self, 
        job_id: str, 
        filename: str, 
        auction_site: str,
        offering_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new CSV upload progress tracking job
        
        Args:
            job_id: Unique job identifier
            filename: Name of the CSV file
            auction_site: Auction site source
            offering_type: Type of domain offering (optional: 'auction', 'backorder', 'buy_now')
            
        Returns:
            Job record dictionary
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            job_data = {
                'job_id': job_id,
                'filename': filename,
                'auction_site': auction_site,
                'status': 'pending',
                'total_records': 0,
                'processed_records': 0,
                'inserted_count': 0,
                'updated_count': 0,
                'skipped_count': 0,
                'deleted_expired_count': 0,
                'current_stage': None,
                'progress_percentage': 0.00
            }
            # Include offering_type if provided
            if offering_type:
                job_data['offering_type'] = offering_type
            
            try:
                result = self.client.table('csv_upload_progress').insert(job_data).execute()
                
                if result.data and len(result.data) > 0:
                    logger.info("Created CSV upload job", job_id=job_id, filename=filename)
                    return result.data[0]
                else:
                    raise Exception("Failed to create job record")
            except Exception as table_error:
                error_str = str(table_error).lower()
                # Check if table doesn't exist (404 or "relation does not exist")
                if '404' in error_str or 'relation' in error_str or 'does not exist' in error_str:
                    logger.warning("csv_upload_progress table not found, attempting to create it", error=str(table_error))
                    # Try to create the table
                    await self._ensure_csv_progress_table_exists()
                    # Retry the insert
                    result = self.client.table('csv_upload_progress').insert(job_data).execute()
                    if result.data and len(result.data) > 0:
                        logger.info("Created CSV upload job after table creation", job_id=job_id, filename=filename)
                        return result.data[0]
                    else:
                        raise Exception("Failed to create job record after table creation")
                else:
                    raise
                
        except Exception as e:
            logger.error("Failed to create CSV upload job", job_id=job_id, error=str(e))
            raise
    
    async def _ensure_csv_progress_table_exists(self):
        """
        Ensure the csv_upload_progress table exists by creating it if needed
        This is a fallback if the migration hasn't been applied yet
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            # Read the migration SQL
            from pathlib import Path
            migration_file = Path(__file__).parent.parent.parent / 'supabase' / 'migrations' / '20250127000000_create_csv_upload_progress_table.sql'
            
            if not migration_file.exists():
                logger.error("Migration file not found", path=str(migration_file))
                raise Exception(f"Migration file not found: {migration_file}")
            
            with open(migration_file, 'r') as f:
                migration_sql = f.read()
            
            # Try to execute SQL via Supabase REST API using RPC
            # Some self-hosted Supabase instances support executing SQL via RPC
            try:
                # Try using the REST API to execute SQL (if supported)
                import httpx
                import json
                
                # Use the service role key for admin operations
                headers = {
                    'apikey': self.settings.SUPABASE_SERVICE_ROLE_KEY or self.settings.SUPABASE_KEY,
                    'Authorization': f'Bearer {self.settings.SUPABASE_SERVICE_ROLE_KEY or self.settings.SUPABASE_KEY}',
                    'Content-Type': 'application/json',
                    'Prefer': 'return=minimal'
                }
                
                # Try to execute via REST API (this may not work for all Supabase instances)
                # For self-hosted Supabase, you typically need to use psql or Supabase Studio
                logger.warning(
                    "csv_upload_progress table does not exist. Attempting automatic creation...",
                    migration_file=str(migration_file)
                )
                
                # Note: Supabase REST API doesn't support direct SQL execution
                # We'll provide helpful error message instead
                raise Exception(
                    "MIGRATION_REQUIRED: The csv_upload_progress table does not exist. "
                    "Please apply the migration manually:\n\n"
                    "1. Run: python backend/apply_csv_progress_migration.py\n"
                    "   OR\n"
                    "2. Open Supabase Studio → SQL Editor → Paste and run the SQL from:\n"
                    f"   {migration_file}\n\n"
                    "After applying the migration, the CSV upload progress tracking will work."
                )
                
            except Exception as e:
                if "MIGRATION_REQUIRED" in str(e):
                    raise
                logger.error("Failed to create table automatically", error=str(e))
                raise Exception(
                    "MIGRATION_REQUIRED: The csv_upload_progress table does not exist. "
                    "Please apply the migration manually:\n\n"
                    "1. Run: python backend/apply_csv_progress_migration.py\n"
                    "   OR\n"
                    "2. Open Supabase Studio → SQL Editor → Paste and run the SQL from:\n"
                    f"   {migration_file}\n\n"
                    "After applying the migration, the CSV upload progress tracking will work."
                )
            
        except Exception as e:
            logger.error("Failed to ensure csv_upload_progress table exists", error=str(e))
            raise
    
    async def update_csv_upload_progress(
        self,
        job_id: str,
        status: Optional[str] = None,
        total_records: Optional[int] = None,
        processed_records: Optional[int] = None,
        inserted_count: Optional[int] = None,
        updated_count: Optional[int] = None,
        skipped_count: Optional[int] = None,
        deleted_expired_count: Optional[int] = None,
        current_stage: Optional[str] = None,
        error_message: Optional[str] = None,
        completed: bool = False
    ) -> Dict[str, Any]:
        """
        Update CSV upload progress
        
        Args:
            job_id: Job identifier
            status: Current status (pending, parsing, processing, completed, failed)
            total_records: Total number of records to process
            processed_records: Number of records processed so far
            inserted_count: Number of records inserted
            updated_count: Number of records updated
            skipped_count: Number of records skipped
            deleted_expired_count: Number of expired records deleted
            current_stage: Current processing stage
            error_message: Error message if failed
            completed: Whether the job is completed
            
        Returns:
            Updated job record
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            update_data: Dict[str, Any] = {}
            
            if status:
                update_data['status'] = status
            if total_records is not None:
                update_data['total_records'] = total_records
            if processed_records is not None:
                update_data['processed_records'] = processed_records
            if inserted_count is not None:
                update_data['inserted_count'] = inserted_count
            if updated_count is not None:
                update_data['updated_count'] = updated_count
            if skipped_count is not None:
                update_data['skipped_count'] = skipped_count
            if deleted_expired_count is not None:
                update_data['deleted_expired_count'] = deleted_expired_count
            if current_stage:
                update_data['current_stage'] = current_stage
            if error_message:
                update_data['error_message'] = error_message
                update_data['status'] = 'failed'
            
            if completed:
                update_data['status'] = 'completed'
                update_data['completed_at'] = datetime.now(timezone.utc).isoformat()
            
            # Calculate progress percentage
            if total_records is not None and processed_records is not None and total_records > 0:
                progress = min(100.00, round((processed_records / total_records) * 100.00, 2))
                update_data['progress_percentage'] = progress
            
            if not update_data:
                # No updates to make
                return await self.get_csv_upload_progress(job_id)
            
            result = (
                self.client.table('csv_upload_progress')
                .update(update_data)
                .eq('job_id', job_id)
                .execute()
            )
            
            if result.data and len(result.data) > 0:
                logger.debug("Updated CSV upload progress", 
                           job_id=job_id, 
                           status=status,
                           processed=processed_records,
                           total=total_records)
                return result.data[0]
            else:
                logger.warning("No data returned from progress update", job_id=job_id)
                return await self.get_csv_upload_progress(job_id)
                
        except Exception as e:
            logger.error("Failed to update CSV upload progress", job_id=job_id, error=str(e))
            raise
    
    async def get_csv_upload_progress(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get CSV upload progress for a job
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job progress record or None if not found
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            result = (
                self.client.table('csv_upload_progress')
                .select('*')
                .eq('job_id', job_id)
                .single()
                .execute()
            )
            
            if result.data:
                return result.data
            else:
                return None
                
        except Exception as e:
            logger.error("Failed to get CSV upload progress", job_id=job_id, error=str(e))
            return None
    
    async def get_latest_active_upload_job(self) -> Optional[Dict[str, Any]]:
        """
        Get the latest active (non-completed, non-failed) CSV upload job progress
        
        Returns:
            Job progress record or None if no active job found
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            result = (
                self.client.table('csv_upload_progress')
                .select('*')
                .not_.eq('status', 'completed')
                .not_.eq('status', 'failed')
                .order('created_at', desc=True)
                .limit(1)
                .execute()
            )
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            else:
                return None
                
        except Exception as e:
            logger.error("Failed to get latest active upload job", error=str(e))
            return None
    
    async def get_default_llm_provider(self) -> Optional[Dict[str, Any]]:
        """
        Get the default LLM provider configuration from the database.
        Returns a dictionary with provider details and the associated API key.
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")

            # 1. Get the default provider
            provider_result = self.client.table('llm_providers')\
                .select('*')\
                .eq('is_default', True)\
                .limit(1)\
                .execute()

            if not provider_result.data:
                logger.warning("No default LLM provider found in llm_providers table")
                return None
            
            provider_row = provider_result.data[0]
            api_keys_id = provider_row.get('api_keys_id')
            
            if not api_keys_id:
                logger.error("Default LLM provider has no api_keys_id linked", provider=provider_row.get('provider'))
                return None

            # 2. Get the API key
            key_result = self.client.table('api_keys')\
                .select('*')\
                .eq('id', api_keys_id)\
                .limit(1)\
                .execute()
                
            if not key_result.data:
                logger.error("API key record not found for default provider", api_keys_id=api_keys_id)
                return None
            
            key_row = key_result.data[0]
            
            return {
                "provider": provider_row.get('provider'),
                "model_name": provider_row.get('model_name'),
                "api_key": key_row.get('key_value'),
                "base_url": key_row.get('base_url')
            }

        except Exception as e:
            logger.error("Failed to fetch default LLM provider", error=str(e))
            return None

    async def get_dataforseo_key(self) -> Optional[Dict[str, str]]:
        """
        Get the active DataForSEO credentials from the api_keys table.
        """
        try:
            if not self.client:
                raise Exception("Supabase client not available")
            
            # Query for active DataForSEO key
            result = self.client.table('api_keys')\
                .select('*')\
                .eq('provider', 'dataforseo')\
                .eq('is_active', True)\
                .limit(1)\
                .execute()
                
            if not result.data:
                logger.warning("No active DataForSEO key found in api_keys table")
                return None
            
            row = result.data[0]
            return {
                "key_value": row.get('key_value'),
                "base_url": row.get('base_url'),
                "user_name": row.get('user_name')
            }
            
        except Exception as e:
            logger.error("Failed to fetch DataForSEO key", error=str(e))
            return None


# Global database service instance
_db_service: Optional[DatabaseService] = None


async def init_database():
    """Initialize database service"""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
        await _db_service.init_database()
    return _db_service


def get_database() -> DatabaseService:
    """Get database service instance"""
    global _db_service
    if _db_service is None:
        raise RuntimeError("Database service not initialized")
    return _db_service
