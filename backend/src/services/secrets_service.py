"""
Secrets service for retrieving API credentials from Supabase
"""

from typing import Dict, Any, Optional
import structlog
from datetime import datetime, timedelta
import json

from services.database import get_database
from utils.config import get_settings

logger = structlog.get_logger()


class SecretsService:
    """Service for managing and retrieving API secrets from Supabase"""
    
    def __init__(self):
        self.db = get_database()
        self.settings = get_settings()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=5)  # Cache secrets for 5 minutes
    
    async def get_secret(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Get credentials for a specific service from Supabase
        
        Args:
            service_name: Name of the service (e.g., 'dataforseo', 'gemini')
            
        Returns:
            Dictionary containing the service credentials, or None if not found
        """
        try:
            # Check cache first
            if self._is_cached(service_name):
                logger.debug("Retrieved secret from cache", service=service_name)
                return self._cache[service_name]
            
            # Query Supabase for the secret
            result = self.db.client.table('secrets').select('credentials').eq('service_name', service_name).eq('is_active', True).execute()
            
            if not result.data:
                logger.warning("Secret not found in database", service=service_name)
                return None
            
            credentials = result.data[0]['credentials']
            
            # Cache the result
            self._cache[service_name] = credentials
            self._cache_expiry[service_name] = datetime.utcnow() + self._cache_ttl
            
            logger.info("Retrieved secret from database", service=service_name)
            return credentials
            
        except Exception as e:
            logger.error("Failed to retrieve secret", service=service_name, error=str(e))
            return None
    
    async def get_dataforseo_credentials(self) -> Optional[Dict[str, str]]:
        """Get DataForSEO credentials"""
        credentials = await self.get_secret('dataforseo')
        if not credentials:
            return None
        
        # Ensure all required fields are present
        required_fields = ['login', 'password', 'api_url']
        if not all(credentials.get(field) for field in required_fields):
            logger.error("DataForSEO credentials missing required fields", 
                        missing=[field for field in required_fields if not credentials.get(field)])
            return None
        
        return {
            'login': credentials.get('login'),
            'password': credentials.get('password'),
            'api_url': credentials.get('api_url')
        }
    
    async def get_gemini_credentials(self) -> Optional[str]:
        """Get Gemini API key"""
        credentials = await self.get_secret('gemini')
        if not credentials:
            return None
        
        return credentials.get('api_key')
    
    async def get_openai_credentials(self) -> Optional[str]:
        """Get OpenAI API key"""
        credentials = await self.get_secret('openai')
        if not credentials:
            return None
        
        return credentials.get('api_key')
    
    async def get_wayback_machine_config(self) -> Dict[str, str]:
        """Get Wayback Machine configuration"""
        credentials = await self.get_secret('wayback_machine')
        if not credentials:
            return {
                'api_url': 'http://web.archive.org/cdx/search/cdx'
            }
        
        return {
            'api_url': credentials.get('api_url', 'http://web.archive.org/cdx/search/cdx')
        }
    
    async def get_google_trends_credentials(self) -> Optional[str]:
        """Get Google Trends API key"""
        credentials = await self.get_secret('google_trends')
        if not credentials:
            return None
        
        return credentials.get('api_key')
    
    async def get_affiliate_credentials(self, network: str) -> Optional[Dict[str, str]]:
        """Get affiliate network credentials"""
        valid_networks = ['shareasale', 'impact', 'amazon_associates', 'cj', 'partnerize']
        
        if network not in valid_networks:
            logger.error("Invalid affiliate network", network=network)
            return None
        
        credentials = await self.get_secret(network)
        if not credentials:
            return None
        
        return credentials
    
    async def get_social_media_credentials(self, platform: str) -> Optional[Dict[str, str]]:
        """Get social media platform credentials"""
        valid_platforms = ['reddit', 'twitter', 'tiktok']
        
        if platform not in valid_platforms:
            logger.error("Invalid social media platform", platform=platform)
            return None
        
        credentials = await self.get_secret(platform)
        if not credentials:
            return None
        
        return credentials
    
    async def get_content_optimization_credentials(self, service: str) -> Optional[str]:
        """Get content optimization service credentials"""
        valid_services = ['surfer_seo', 'frase', 'coschedule']
        
        if service not in valid_services:
            logger.error("Invalid content optimization service", service=service)
            return None
        
        credentials = await self.get_secret(service)
        if not credentials:
            return None
        
        return credentials.get('api_key')
    
    async def get_export_credentials(self, platform: str) -> Optional[Dict[str, str]]:
        """Get export platform credentials"""
        valid_platforms = ['google_docs', 'notion', 'wordpress']
        
        if platform not in valid_platforms:
            logger.error("Invalid export platform", platform=platform)
            return None
        
        credentials = await self.get_secret(platform)
        if not credentials:
            return None
        
        return credentials
    
    async def get_linkup_credentials(self) -> Optional[str]:
        """Get LinkUp API credentials"""
        credentials = await self.get_secret('linkup')
        if not credentials:
            return None
        
        return credentials.get('api_key')
    
    def _is_cached(self, service_name: str) -> bool:
        """Check if secret is cached and not expired"""
        if service_name not in self._cache:
            return False
        
        if service_name not in self._cache_expiry:
            return False
        
        return datetime.utcnow() < self._cache_expiry[service_name]
    
    async def clear_cache(self, service_name: Optional[str] = None):
        """Clear cache for a specific service or all services"""
        if service_name:
            self._cache.pop(service_name, None)
            self._cache_expiry.pop(service_name, None)
            logger.info("Cleared cache for service", service=service_name)
        else:
            self._cache.clear()
            self._cache_expiry.clear()
            logger.info("Cleared all cached secrets")
    
    async def update_secret(self, service_name: str, credentials: Dict[str, Any]) -> bool:
        """
        Update secret in Supabase (requires service role)
        
        Args:
            service_name: Name of the service
            credentials: New credentials dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.db.client.table('secrets').upsert({
                'service_name': service_name,
                'credentials': credentials,
                'is_active': True,
                'updated_at': datetime.utcnow().isoformat()
            }).execute()
            
            if result.data:
                # Clear cache for this service
                await self.clear_cache(service_name)
                logger.info("Updated secret in database", service=service_name)
                return True
            else:
                logger.error("Failed to update secret", service=service_name)
                return False
                
        except Exception as e:
            logger.error("Failed to update secret", service=service_name, error=str(e))
            return False
    
    
# Global secrets service instance
_secrets_service: Optional[SecretsService] = None


def get_secrets_service() -> SecretsService:
    """Get secrets service instance (singleton pattern)"""
    global _secrets_service
    if _secrets_service is None:
        _secrets_service = SecretsService()
    return _secrets_service
