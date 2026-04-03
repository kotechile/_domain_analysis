"""
Health check API routes
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
import structlog
import asyncio
import time

from models.domain_analysis import HealthResponse
from services.database import get_database, init_database
from services.external_apis import DataForSEOService, WaybackMachineService, LLMService
from services.secrets_service import get_secrets_service

logger = structlog.get_logger()
router = APIRouter()


@dataclass
class CachedHealth:
    """Cached health check result with TTL"""
    status: str
    services: dict
    timestamp: datetime
    expires_at: float


# Simple in-memory cache with 15-second TTL
_health_cache: Optional[CachedHealth] = None
_CACHE_TTL_SECONDS = 15


def _is_cache_valid() -> bool:
    """Check if cached health check is still valid"""
    global _health_cache
    if _health_cache is None:
        return False
    return time.time() < _health_cache.expires_at


def _get_cached_health() -> Optional[CachedHealth]:
    """Get cached health if valid"""
    if _is_cache_valid():
        return _health_cache
    return None


def _set_cached_health(status: str, services: dict) -> None:
    """Cache health check result"""
    global _health_cache
    _health_cache = CachedHealth(
        status=status,
        services=services,
        timestamp=datetime.utcnow(),
        expires_at=time.time() + _CACHE_TTL_SECONDS
    )


async def check_service_with_timeout(service_name: str, check_func, timeout: float = 5.0, retries: int = 1):
    """Check a service with timeout and optional retry for transient failures"""
    last_error = None
    for attempt in range(retries + 1):
        try:
            result = await asyncio.wait_for(check_func(), timeout=timeout)
            return 'healthy' if result else 'degraded'
        except asyncio.TimeoutError:
            last_error = f"timed out after {timeout}s"
            if attempt < retries:
                await asyncio.sleep(0.5)  # Brief pause before retry
        except Exception as e:
            last_error = str(e)

    logger.warning(f"{service_name} health check failed: {last_error}")
    return 'degraded'


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    Returns the status of the application and all external services
    Optimized with caching (15s TTL) and timeouts to prevent slow responses
    """
    # Check cache first
    cached = _get_cached_health()
    if cached:
        return HealthResponse(
            status=cached.status,
            services=cached.services,
            timestamp=cached.timestamp
        )

    try:
        services_status = {}

        # 1) Check database connection (single query, longer timeout)
        try:
            from utils.config import get_settings
            settings = get_settings()
            supabase_url = settings.SUPABASE_URL.rstrip('/') if settings.SUPABASE_URL else None
            if not supabase_url:
                services_status['database'] = 'unhealthy'
                logger.error("SUPABASE_URL is not set in environment variables")

            try:
                db = get_database()
            except RuntimeError:
                try:
                    db = await init_database()
                except Exception as init_error:
                    logger.debug("init_database failed, trying new instance", error=str(init_error))
                    from services.database import DatabaseService
                    db = DatabaseService()

            if db.client is None:
                services_status['database'] = 'unhealthy'
                logger.warning("Database client not initialized")
            else:
                async def db_check():
                    # Single query to check database connectivity
                    await (await db._get_client()).table('reports').select('id').limit(1).execute()
                    return True

                db_status = await check_service_with_timeout('database', db_check, timeout=8.0, retries=1)
                services_status['database'] = db_status

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.warning("Database health check failed", error=error_msg, error_type=error_type, exc_info=True)
            services_status['database'] = 'unhealthy'

        # 2) Check external APIs with timeouts (run in parallel for speed)
        async def check_dataforseo():
            # Only verify credentials exist, no HTTP call needed
            service = DataForSEOService()
            credentials = await service._get_credentials()
            return credentials is not None

        async def check_wayback():
            service = WaybackMachineService()
            return await service.health_check()

        async def check_llm():
            service = LLMService()
            provider, api_key, _ = await service._get_provider_and_key()
            return provider is not None and api_key is not None

        # Run external API checks in parallel with reasonable timeouts
        dataforseo_status, wayback_status, llm_status = await asyncio.gather(
            check_service_with_timeout('DataForSEO', check_dataforseo, timeout=5.0, retries=1),
            check_service_with_timeout('Wayback Machine', check_wayback, timeout=8.0, retries=1),
            check_service_with_timeout('LLM', check_llm, timeout=5.0, retries=1)
        )

        services_status['dataforseo'] = dataforseo_status
        services_status['wayback_machine'] = wayback_status
        services_status['llm'] = llm_status
        
        # Determine overall status - only database is CRITICAL for 'unhealthy' vs 'healthy'
        # External APIs being down makes us 'degraded' but still functional
        if services_status.get('database') == 'healthy':
            if all(status == 'healthy' for status in services_status.values()):
                overall_status = 'healthy'
            else:
                overall_status = 'degraded'
        else:
            overall_status = 'unhealthy'

        # Cache the result for future requests
        _set_cached_health(overall_status, services_status)

        return HealthResponse(
            status=overall_status,
            services=services_status,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness check endpoint
    Returns whether the application is ready to accept requests
    """
    try:
        # Check if all critical services are available
        db = get_database()
        await (await db._get_client()).table('reports').select('id').limit(1).execute()
        
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check endpoint
    Returns whether the application is alive
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/database-diagnostic")
async def database_diagnostic():
    """
    Detailed database diagnostic endpoint
    Returns detailed information about database connection issues
    """
    import os
    diagnostic = { "timestamp": datetime.utcnow().isoformat(), "checks": {} }
    
    # Check 1: Environment variables
    try:
        from utils.config import get_settings
        settings = get_settings()
        env_url = os.environ.get('SUPABASE_URL', 'NOT SET IN ENV')
        diagnostic["checks"]["environment"] = { "status": "ok", "supabase_url_set": bool(settings.SUPABASE_URL), "supabase_url_preview": settings.SUPABASE_URL[:50] + "..." if settings.SUPABASE_URL else None, "supabase_url_full": settings.SUPABASE_URL if settings.SUPABASE_URL else None, "supabase_url_from_env_var": env_url[:50] + "..." if env_url != 'NOT SET IN ENV' else env_url, "supabase_key_set": bool(settings.SUPABASE_KEY), "supabase_key_length": len(settings.SUPABASE_KEY) if settings.SUPABASE_KEY else 0, "supabase_service_role_key_set": bool(settings.SUPABASE_SERVICE_ROLE_KEY), "supabase_verify_ssl": getattr(settings, 'SUPABASE_VERIFY_SSL', True) }
    except Exception as e:
        diagnostic["checks"]["environment"] = { "status": "error", "error": str(e), "error_type": type(e).__name__ }
        return diagnostic
    
    # Check 2: Database service initialization
    try:
        from services.database import DatabaseService
        db = DatabaseService()
        diagnostic["checks"]["client_initialization"] = { "status": "ok" if db.client is not None else "failed", "client_is_none": db.client is None }
        if db.client is None:
            return diagnostic
    except Exception as e:
        diagnostic["checks"]["client_initialization"] = { "status": "error", "error": str(e), "error_type": type(e).__name__ }
        return diagnostic
    
    # Check 3: Async init
    try:
        db = await init_database()
        diagnostic["checks"]["async_init"] = { "status": "ok" if db.client is not None else "failed", "client_is_none": db.client is None }
        if db.client is None:
            return diagnostic
    except Exception as e:
        diagnostic["checks"]["async_init"] = { "status": "error", "error": str(e), "error_type": type(e).__name__ }
        return diagnostic
    
    # Check 4: Secrets table access
    try:
        result = await (await db._get_client()).table('secrets').select('id').limit(1).execute()
        diagnostic["checks"]["secrets_table"] = { "status": "ok", "records_found": len(result.data) }
    except Exception as e:
        diagnostic["checks"]["secrets_table"] = { "status": "error", "error": str(e), "error_type": type(e).__name__ }
        return diagnostic
    
    # Check 5: Reports table access
    try:
        result = await (await db._get_client()).table('reports').select('id').limit(1).execute()
        diagnostic["checks"]["reports_table"] = { "status": "ok", "records_found": len(result.data) }
    except Exception as e:
        diagnostic["checks"]["reports_table"] = { "status": "error", "error": str(e), "error_type": type(e).__name__ }
    
    return diagnostic



@router.post("/health/clear-cache")
async def clear_credentials_cache():
    """
    Clear credentials cache to force refresh from Supabase
    Useful when credentials are updated in the database
    """
    try:
        logger.info("Clearing credentials cache")
        
        # Clear secrets service cache
        secrets_service = get_secrets_service()
        await secrets_service.clear_cache('dataforseo')
        
        # Note: Service instances are created per request, so their internal caches
        # will be cleared automatically on the next request
        
        logger.info("Credentials cache cleared successfully")
        return { "status": "success", "message": "Credentials cache cleared. New credentials will be fetched on next request.", "timestamp": datetime.utcnow().isoformat() }
        
    except Exception as e:
        logger.error("Failed to clear credentials cache", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@router.get("/health/test-db-connection")
async def test_db_connection():
    """
    Test database connection by checking critical tables
    Specifically checks csv_upload_progress and auctions access
    """
    results = { "timestamp": datetime.utcnow().isoformat(), "connection": "unknown", "csv_upload_progress_exists": False, "auctions_exists": False, "auctions_staging_exists": False, "write_test": False, "error": None }
    
    try:
        db = get_database()
        if not db.client:
            await init_database()
            db = get_database()
        
        if not db.client:
            results["error"] = "Could not initialize database client"
            return results
            
        results["connection"] = "connected"
        
        # Test 1: Check csv_upload_progress
        try:
            # Try to select 1 record, if table doesn't exist it triggers error
            await (await db._get_client()).table('csv_upload_progress').select('job_id').limit(1).execute()
            results["csv_upload_progress_exists"] = True
        except Exception as e:
            results["error"] = f"csv_upload_progress table error: {str(e)}"
            return results
            
        # Test 2: Check auctions
        try:
            await (await db._get_client()).table('auctions').select('id').limit(1).execute()
            results["auctions_exists"] = True
        except Exception as e:
             results["error"] = f"auctions table error: {str(e)}"
             
        # Test 3: Check auctions_staging
        try:
            await (await db._get_client()).table('auctions_staging').select('domain').limit(1).execute()
            results["auctions_staging_exists"] = True
        except Exception as e:
             results["error"] = f"auctions_staging table error: {str(e)}"

        # Test 4: Write test to csv_upload_progress
        try:
            import uuid
            test_id = str(uuid.uuid4())
            await (await db._get_client()).table('csv_upload_progress').insert({ 'job_id': f"test_{test_id}", 'filename': 'test_connectivity.csv', 'auction_site': 'test', 'status': 'test' }).execute()
            
            # Cleanup
            await (await db._get_client()).table('csv_upload_progress').delete().eq('job_id', f"test_{test_id}").execute()
            results["write_test"] = True
        except Exception as e:
            results["error"] = f"Write failed: {str(e)}"
            
        return results
        
    except Exception as e:
        results["error"] = f"Global error: {str(e)}"
        return results

