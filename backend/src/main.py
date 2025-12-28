"""
Domain Analysis System - FastAPI Backend
Main application entry point
"""

import sys
from pathlib import Path

# Add src directory to Python path to ensure imports work
# This allows running from backend directory with: python -m uvicorn src.main:app
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog
from contextlib import asynccontextmanager

from api.routes import analysis, reports, health, development_plan, n8n_webhook, bulk_analysis, auctions, filters
from api.routes import debug_offer_type
from services.database import init_database
from services.cache import init_cache
from utils.config import get_settings

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events"""
    # Startup
    logger.info("Starting Domain Analysis System")
    try:
        await init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
    
    try:
        await init_cache()
        logger.info("Cache initialized successfully")
    except Exception as e:
        logger.warning("Cache initialization failed", error=str(e))
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Domain Analysis System")


# Initialize FastAPI application
app = FastAPI(
    title="Domain Analysis System",
    description="Comprehensive domain analysis with SEO data, backlinks, and LLM-powered insights",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add trusted host middleware for security
# Note: Disable when N8N is enabled (requests come through ngrok with dynamic domains)
# In production with a fixed domain, re-enable this with your actual domain
if not settings.N8N_ENABLED:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )
else:
    logger.warning("TrustedHostMiddleware disabled - N8N enabled, requests come through ngrok")

# Include API routes
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])
app.include_router(reports.router, prefix="/api/v1", tags=["reports"])
app.include_router(development_plan.router, prefix="/api/v1", tags=["development-plan"])
app.include_router(n8n_webhook.router, prefix="/api/v1", tags=["n8n"])
app.include_router(bulk_analysis.router, prefix="/api/v1/bulk-analysis", tags=["bulk-analysis"])
app.include_router(auctions.router, prefix="/api/v1", tags=["auctions"])
app.include_router(filters.router, prefix="/api/v1", tags=["filters"])
app.include_router(debug_offer_type.router, prefix="/api/v1", tags=["debug"])


@app.get("/")
async def root():
    """Root endpoint with basic API information"""
    return {
        "message": "Domain Analysis System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
