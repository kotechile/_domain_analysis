"""
Cache service for Redis integration
"""

import redis.asyncio as redis
from typing import Optional, Any
import json
import structlog
from datetime import timedelta

from utils.config import get_settings

logger = structlog.get_logger()


class CacheService:
    """Redis-based cache service"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client: Optional[redis.Redis] = None
        self.default_ttl = self.settings.CACHE_TTL_SECONDS
    
    async def init_cache(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                self.settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Redis cache", error=str(e))
            # Continue without cache if Redis is not available
            self.redis_client = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning("Cache get failed", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if not self.redis_client:
            return False
        
        try:
            ttl = ttl or self.default_ttl
            await self.redis_client.setex(
                key, 
                ttl, 
                json.dumps(value, default=str)
            )
            return True
        except Exception as e:
            logger.warning("Cache set failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning("Cache delete failed", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis_client:
            return False
        
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.warning("Cache exists check failed", key=key, error=str(e))
            return False
    
    async def get_or_set(self, key: str, factory_func, ttl: Optional[int] = None) -> Any:
        """Get value from cache or set it using factory function"""
        value = await self.get(key)
        if value is not None:
            return value
        
        # Generate value using factory function
        if asyncio.iscoroutinefunction(factory_func):
            value = await factory_func()
        else:
            value = factory_func()
        
        # Cache the value
        await self.set(key, value, ttl)
        return value
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self.redis_client:
            return 0
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning("Cache pattern clear failed", pattern=pattern, error=str(e))
            return 0
    
    async def get_stats(self) -> dict:
        """Get cache statistics"""
        if not self.redis_client:
            return {"status": "disabled"}
        
        try:
            info = await self.redis_client.info()
            return {
                "status": "active",
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            logger.warning("Cache stats failed", error=str(e))
            return {"status": "error", "error": str(e)}


# Global cache service instance
_cache_service: Optional[CacheService] = None


async def init_cache():
    """Initialize cache service"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
        await _cache_service.init_cache()
    return _cache_service


def get_cache() -> Optional[CacheService]:
    """Get cache service instance"""
    global _cache_service
    return _cache_service
