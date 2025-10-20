"""
Health check API routes
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
import structlog

from models.domain_analysis import HealthResponse
from services.database import get_database
from services.external_apis import DataForSEOService, WaybackMachineService, LLMService

logger = structlog.get_logger()
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    Returns the status of the application and all external services
    """
    try:
        services_status = {}
        
        # Check database connection
        try:
            db = get_database()
            # Simple query to test connection
            db.client.table('reports').select('id').limit(1).execute()
            services_status['database'] = 'healthy'
        except Exception as e:
            logger.warning("Database health check failed", error=str(e))
            services_status['database'] = 'unhealthy'
        
        # Check external APIs (basic connectivity)
        try:
            dataforseo_service = DataForSEOService()
            await dataforseo_service.health_check()
            services_status['dataforseo'] = 'healthy'
        except Exception as e:
            logger.warning("DataForSEO health check failed", error=str(e))
            services_status['dataforseo'] = 'unhealthy'
        
        try:
            wayback_service = WaybackMachineService()
            await wayback_service.health_check()
            services_status['wayback_machine'] = 'healthy'
        except Exception as e:
            logger.warning("Wayback Machine health check failed", error=str(e))
            services_status['wayback_machine'] = 'unhealthy'
        
        try:
            llm_service = LLMService()
            await llm_service.health_check()
            services_status['llm'] = 'healthy'
        except Exception as e:
            logger.warning("LLM service health check failed", error=str(e))
            services_status['llm'] = 'unhealthy'
        
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
