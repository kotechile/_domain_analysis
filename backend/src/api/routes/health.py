"""
Health check API routes
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
import structlog
import asyncio

from models.domain_analysis import HealthResponse
from services.database import get_database, init_database
from services.external_apis import DataForSEOService, WaybackMachineService, LLMService
from services.secrets_service import get_secrets_service

logger = structlog.get_logger()
router = APIRouter()


async def check_service_with_timeout(service_name: str, check_func, timeout: float = 2.0):
    """Check a service with a timeout"""
    try:
        await asyncio.wait_for(check_func(), timeout=timeout)
        return 'healthy'
    except asyncio.TimeoutError:
        logger.warning(f"{service_name} health check timed out after {timeout}s")
        return 'degraded'
    except Exception as e:
        logger.warning(f"{service_name} health check failed", error=str(e))
        return 'unhealthy'


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    Returns the status of the application and all external services
    Optimized with timeouts to prevent slow responses
    """
    try:
        services_status = {}
        
        # Check database connection (critical, no timeout)
        try:
            # Verify URL configuration first
            from utils.config import get_settings
            settings = get_settings()
            supabase_url = settings.SUPABASE_URL.rstrip('/') if settings.SUPABASE_URL else None
            if not supabase_url:
                services_status['database'] = 'unhealthy'
                logger.error("SUPABASE_URL is not set in environment variables")
            elif 'sb_domain' in supabase_url and 'sbdomain' not in supabase_url:
                # Warn about potential URL mismatch (underscore vs no underscore)
                logger.warning("SUPABASE_URL contains 'sb_domain' - verify this matches your actual server URL", 
                            url=supabase_url)
            
            # Try to get or initialize database
            # If init_database fails due to table creation, that's okay - we just need the client
            try:
                db = await init_database()
            except Exception as init_error:
                # If init fails, try to get existing instance or create a new one
                logger.debug("init_database failed, trying to get existing instance", error=str(init_error))
                from services.database import get_database, DatabaseService
                try:
                    db = get_database()
                except RuntimeError:
                    # No existing instance, create a new one (client should still be initialized)
                    db = DatabaseService()
            
            if db.client is None:
                services_status['database'] = 'unhealthy'
                logger.warning("Database client not initialized - check SUPABASE_URL and SUPABASE_KEY environment variables")
            else:
                # Test with secrets table first (known to exist)
                try:
                    result = db.client.table('secrets').select('id').limit(1).execute()
                    # Test reports table access
                    try:
                        db.client.table('reports').select('id').limit(1).execute()
                        services_status['database'] = 'healthy'
                        logger.info("Database connection healthy - all tables accessible")
                    except Exception as table_error:
                        error_msg = str(table_error)
                        error_type = type(table_error).__name__
                        # Check for connection pool or server availability issues
                        if 'no available server' in error_msg.lower() or '503' in error_msg:
                            logger.warning("Database connection pool exhausted or server unavailable", 
                                        error=error_msg, error_type=error_type)
                            services_status['database'] = 'degraded'  # Temporary connection issue
                        else:
                            logger.warning("Reports table not accessible", error=error_msg, error_type=error_type)
                            services_status['database'] = 'degraded'  # Connection works but some tables missing
                except Exception as secrets_error:
                    error_msg = str(secrets_error)
                    error_type = type(secrets_error).__name__
                    # Check for connection pool or server availability issues
                    if 'no available server' in error_msg.lower() or '503' in error_msg:
                        logger.warning("Database connection pool exhausted or server unavailable", 
                                    error=error_msg, error_type=error_type)
                        services_status['database'] = 'degraded'  # Temporary connection issue, not completely unhealthy
                    else:
                        logger.warning("Secrets table not accessible", error=error_msg, error_type=error_type)
                        services_status['database'] = 'unhealthy'
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.warning("Database health check failed", error=error_msg, error_type=error_type, exc_info=True)
            services_status['database'] = 'unhealthy'
        
        # Check external APIs with timeouts (run in parallel for speed)
        async def check_dataforseo():
            service = DataForSEOService()
            await service.health_check()
        
        async def check_wayback():
            service = WaybackMachineService()
            await service.health_check()
        
        async def check_llm():
            service = LLMService()
            await service.health_check()
        
        # Run external API checks in parallel with timeouts
        services_status['dataforseo'] = await check_service_with_timeout(
            'DataForSEO', check_dataforseo, timeout=3.0
        )
        services_status['wayback_machine'] = await check_service_with_timeout(
            'Wayback Machine', check_wayback, timeout=3.0
        )
        services_status['llm'] = await check_service_with_timeout(
            'LLM', check_llm, timeout=3.0
        )
        
        # Determine overall status
        overall_status = 'healthy' if all(status == 'healthy' for status in services_status.values()) else 'degraded'
        
        return HealthResponse(
            status=overall_status,
            services=services_status
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
        db.client.table('reports').select('id').limit(1).execute()
        
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
    diagnostic = {
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Check 1: Environment variables
    try:
        from utils.config import get_settings
        settings = get_settings()
        env_url = os.environ.get('SUPABASE_URL', 'NOT SET IN ENV')
        diagnostic["checks"]["environment"] = {
            "status": "ok",
            "supabase_url_set": bool(settings.SUPABASE_URL),
            "supabase_url_preview": settings.SUPABASE_URL[:50] + "..." if settings.SUPABASE_URL else None,
            "supabase_url_full": settings.SUPABASE_URL if settings.SUPABASE_URL else None,
            "supabase_url_from_env_var": env_url[:50] + "..." if env_url != 'NOT SET IN ENV' else env_url,
            "supabase_key_set": bool(settings.SUPABASE_KEY),
            "supabase_key_length": len(settings.SUPABASE_KEY) if settings.SUPABASE_KEY else 0,
            "supabase_service_role_key_set": bool(settings.SUPABASE_SERVICE_ROLE_KEY),
            "supabase_verify_ssl": getattr(settings, 'SUPABASE_VERIFY_SSL', True)
        }
    except Exception as e:
        diagnostic["checks"]["environment"] = {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }
        return diagnostic
    
    # Check 2: Database service initialization
    try:
        from services.database import DatabaseService
        db = DatabaseService()
        diagnostic["checks"]["client_initialization"] = {
            "status": "ok" if db.client is not None else "failed",
            "client_is_none": db.client is None
        }
        if db.client is None:
            return diagnostic
    except Exception as e:
        diagnostic["checks"]["client_initialization"] = {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }
        return diagnostic
    
    # Check 3: Async init
    try:
        db = await init_database()
        diagnostic["checks"]["async_init"] = {
            "status": "ok" if db.client is not None else "failed",
            "client_is_none": db.client is None
        }
        if db.client is None:
            return diagnostic
    except Exception as e:
        diagnostic["checks"]["async_init"] = {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }
        return diagnostic
    
    # Check 4: Secrets table access
    try:
        result = db.client.table('secrets').select('id').limit(1).execute()
        diagnostic["checks"]["secrets_table"] = {
            "status": "ok",
            "records_found": len(result.data)
        }
    except Exception as e:
        diagnostic["checks"]["secrets_table"] = {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }
        return diagnostic
    
    # Check 5: Reports table access
    try:
        result = db.client.table('reports').select('id').limit(1).execute()
        diagnostic["checks"]["reports_table"] = {
            "status": "ok",
            "records_found": len(result.data)
        }
    except Exception as e:
        diagnostic["checks"]["reports_table"] = {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }
    
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
        return {
            "status": "success",
            "message": "Credentials cache cleared. New credentials will be fetched on next request.",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to clear credentials cache", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@router.get("/health/test-db-connection")
async def test_db_connection():
    """
    Test database connection by checking critical tables
    Specifically checks csv_upload_progress and auctions access
    """
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "connection": "unknown",
        "csv_upload_progress_exists": False,
        "auctions_exists": False,
        "auctions_staging_exists": False,
        "write_test": False,
        "error": None
    }
    
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
            db.client.table('csv_upload_progress').select('job_id').limit(1).execute()
            results["csv_upload_progress_exists"] = True
        except Exception as e:
            results["error"] = f"csv_upload_progress table error: {str(e)}"
            return results
            
        # Test 2: Check auctions
        try:
            db.client.table('auctions').select('id').limit(1).execute()
            results["auctions_exists"] = True
        except Exception as e:
             results["error"] = f"auctions table error: {str(e)}"
             
        # Test 3: Check auctions_staging
        try:
            db.client.table('auctions_staging').select('domain').limit(1).execute()
            results["auctions_staging_exists"] = True
        except Exception as e:
             results["error"] = f"auctions_staging table error: {str(e)}"

        # Test 4: Write test to csv_upload_progress
        try:
            import uuid
            test_id = str(uuid.uuid4())
            db.client.table('csv_upload_progress').insert({
                'job_id': f"test_{test_id}",
                'filename': 'test_connectivity.csv',
                'auction_site': 'test',
                'status': 'test'
            }).execute()
            
            # Cleanup
            db.client.table('csv_upload_progress').delete().eq('job_id', f"test_{test_id}").execute()
            results["write_test"] = True
        except Exception as e:
            results["error"] = f"Write failed: {str(e)}"
            
        return results
        
    except Exception as e:
        results["error"] = f"Global error: {str(e)}"
        return results

