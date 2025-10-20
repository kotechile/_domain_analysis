"""
Database service for Supabase integration
"""

from supabase import create_client, Client
from typing import Optional, Dict, Any, List
import structlog
from datetime import datetime, timedelta

from utils.config import get_settings
from models.domain_analysis import DomainAnalysisReport, RawDataCache, DataSource

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
            self.client = create_client(
                self.settings.SUPABASE_URL,
                self.settings.SUPABASE_KEY
            )
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Supabase client", error=str(e))
            raise
    
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
            
            result = self.client.table('reports').upsert({
                'domain_name': report.domain_name,
                'analysis_timestamp': report_data['analysis_timestamp'],
                'status': report.status.value,
                'data_for_seo_metrics': report_data.get('data_for_seo_metrics'),
                'wayback_machine_summary': report_data.get('wayback_machine_summary'),
                'llm_analysis': report_data.get('llm_analysis'),
                'raw_data_links': report_data.get('raw_data_links'),
                'processing_time_seconds': report.processing_time_seconds,
                'error_message': report.error_message,
                'updated_at': datetime.utcnow().isoformat()
            }).execute()
            
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
                raw_data_links=report_data.get('raw_data_links'),
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
                if datetime.utcnow() > expires_at:
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
