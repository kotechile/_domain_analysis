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
        Legacy method for backward compatibility, attempting to map new schema to old return format.
        Ideally, use specific getter methods.
        """
        if service_name == 'dataforseo':
            creds = await self.get_dataforseo_credentials()
            return creds if creds else None
        elif service_name in ['gemini', 'openai']:
            # This is a bit hacky for the generic get_secret, but supports legacy callers
            key = await self._get_llm_api_key(service_name)
            return {'api_key': key} if key else None
        
        # Fallback for other services (social media, affiliates) - assuming they are in api_keys
        # simple lookup by provider name
        try:
            if self._is_cached(service_name):
                return self._cache[service_name]

            result = self.db.client.table('api_keys').select('key_value, user_name, password, base_url').eq('provider', service_name).eq('is_active', True).limit(1).execute()
            
            if result.data:
                row = result.data[0]
                # Map to generic dict
                credentials = {
                    'api_key': row.get('key_value'),
                    'login': row.get('user_name'),
                    'username': row.get('user_name'),
                    'password': row.get('password'),
                    'api_url': row.get('base_url')
                }
                # Remove None values
                credentials = {k: v for k, v in credentials.items() if v is not None}
                
                self._cache[service_name] = credentials
                self._cache_expiry[service_name] = datetime.utcnow() + self._cache_ttl
                return credentials
            return None
        except Exception as e:
            logger.error(f"Failed to fetch generic secret for {service_name}", error=str(e))
            return None

    async def get_dataforseo_credentials(self) -> Optional[Dict[str, str]]:
        """Get DataForSEO credentials from api_keys table"""
        try:
            if self._is_cached('dataforseo'):
                return self._cache['dataforseo']

            # DataForSEO might be stored with provider='dataforseo'
            result = self.db.client.table('api_keys')\
                .select('user_name, password, base_url')\
                .eq('provider', 'dataforseo')\
                .eq('is_active', True)\
                .limit(1)\
                .execute()

            if not result.data:
                logger.warning("DataForSEO credentials not found in api_keys table")
                return None

            row = result.data[0]
            credentials = {
                'login': row.get('user_name'),
                'password': row.get('password'),
                'api_url': row.get('base_url')
            }

            # Validate
            if not credentials['login'] or not credentials['password']:
                logger.error("DataForSEO credentials missing login or password")
                return None

            self._cache['dataforseo'] = credentials
            self._cache_expiry['dataforseo'] = datetime.utcnow() + self._cache_ttl
            
            return credentials

        except Exception as e:
            logger.error("Failed to retrieve DataForSEO credentials", error=str(e))
            return None
    
    async def _get_llm_api_key(self, provider: str) -> Optional[str]:
        """
        Helper to get LLM API key by:
        1. Finding default model for provider in llm_providers
        2. Getting api_keys_id from that model
        3. Fetching key_value from api_keys
        """
        cache_key = f"{provider}_api_key"
        if self._is_cached(cache_key):
            return self._cache[cache_key].get('active_key')

        try:
            # 1. Find default active model for this provider
            model_result = self.db.client.table('llm_providers')\
                .select('api_keys_id')\
                .eq('provider', provider)\
                .eq('is_active', True)\
                .eq('is_default', True)\
                .limit(1)\
                .execute()

            if not model_result.data:
                logger.warning(f"No default active model found for {provider} in llm_providers")
                return None
            
            api_keys_id = model_result.data[0].get('api_keys_id')
            if not api_keys_id:
                logger.error(f"Default model for {provider} has no api_keys_id")
                return None

            # 2. Fetch the actual key
            key_result = self.db.client.table('api_keys')\
                .select('key_value')\
                .eq('id', api_keys_id)\
                .single()\
                .execute()
            
            if not key_result.data:
                logger.error(f"API key not found for ID {api_keys_id}")
                return None

            api_key = key_result.data.get('key_value')
            
            self._cache[cache_key] = {'active_key': api_key}
            self._cache_expiry[cache_key] = datetime.utcnow() + self._cache_ttl
            
            return api_key

        except Exception as e:
            logger.error(f"Failed to retrieve API key for {provider}", error=str(e))
            return None

    async def get_gemini_credentials(self) -> Optional[str]:
        """Get Gemini API key"""
        return await self._get_llm_api_key('gemini')
    
    async def get_openai_credentials(self) -> Optional[str]:
        """Get OpenAI API key"""
        return await self._get_llm_api_key('openai')
    
    async def get_wayback_machine_config(self) -> Dict[str, str]:
        """Get Wayback Machine configuration"""
        # Usually checking generic secret or just returning default
        creds = await self.get_secret('wayback_machine')
        return {
            'api_url': creds.get('api_url', 'http://web.archive.org/cdx/search/cdx') if creds else 'http://web.archive.org/cdx/search/cdx'
        }
    
    async def get_google_trends_credentials(self) -> Optional[str]:
        """Get Google Trends API key"""
        creds = await self.get_secret('google_trends')
        return creds.get('api_key') if creds else None
    
    async def get_affiliate_credentials(self, network: str) -> Optional[Dict[str, str]]:
        """Get affiliate network credentials"""
        return await self.get_secret(network)
    
    async def get_social_media_credentials(self, platform: str) -> Optional[Dict[str, str]]:
        """Get social media platform credentials"""
        return await self.get_secret(platform)
    
    async def get_content_optimization_credentials(self, service: str) -> Optional[str]:
        """Get content optimization service credentials"""
        creds = await self.get_secret(service)
        return creds.get('api_key') if creds else None
    
    async def get_export_credentials(self, platform: str) -> Optional[Dict[str, str]]:
        """Get export platform credentials"""
        return await self.get_secret(platform)
    
    async def get_linkup_credentials(self) -> Optional[str]:
        """Get LinkUp API credentials"""
        creds = await self.get_secret('linkup')
        return creds.get('api_key') if creds else None
    
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
            # Also clear specific helper keys if applicable
            self._cache.pop(f"{service_name}_api_key", None)
            self._cache_expiry.pop(f"{service_name}_api_key", None)
            logger.info("Cleared cache for service", service=service_name)
        else:
            self._cache.clear()
            self._cache_expiry.clear()
            logger.info("Cleared all cached secrets")
    
    async def update_secret(self, service_name: str, credentials: Dict[str, Any]) -> bool:
        """
        Update secret in Supabase
        Note: This legacy implementation might need updates to write to api_keys table correctly,
        but for now we mostly read. Writing complex logic for update to specific tables is skipped
        to minimize risk, as this tool seems primarily for deployment fixing.
        """
        logger.warning("Update secret not fully implemented for new schema", service=service_name)
        return False


# Global secrets service instance
_secrets_service: Optional[SecretsService] = None


def get_secrets_service() -> SecretsService:
    """Get secrets service instance (singleton pattern)"""
    global _secrets_service
    if _secrets_service is None:
        _secrets_service = SecretsService()
    return _secrets_service
