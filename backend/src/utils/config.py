"""
Configuration management for the Domain Analysis System
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application settings
    APP_NAME: str = "Domain Analysis System"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001", "http://localhost:3010"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "*.ngrok-free.dev", "*.ngrok.io", "*.ngrok.app"]
    
    # Database settings (Supabase) - ESSENTIAL SECRETS
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_VERIFY_SSL: bool = True  # Set to False for self-hosted instances with self-signed certificates
    
    # Cache settings
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL_SECONDS: int = 2592000  # 30 days
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10
    
    # Analysis settings
    MAX_ANALYSIS_TIME_SECONDS: int = 15
    MAX_CONCURRENT_ANALYSES: int = 10
    MAX_KEYWORDS_PER_DOMAIN: int = 1000
    MAX_BACKLINKS_PER_DOMAIN: int = 1000  # Increased for detailed analysis
    
    # Async DataForSEO settings
    DATAFORSEO_ASYNC_ENABLED: bool = True
    DATAFORSEO_ASYNC_POLL_INTERVAL: int = 2  # seconds
    DATAFORSEO_ASYNC_MAX_ATTEMPTS: int = 30  # 1 minute max
    DATAFORSEO_ASYNC_TIMEOUT: int = 30  # seconds
    
    # Cache settings for detailed data
    DETAILED_DATA_CACHE_TTL_HOURS: int = 24
    DETAILED_DATA_FRESH_THRESHOLD_HOURS: int = 24
    
    # Dual-mode operation settings
    ANALYSIS_MODE_DEFAULT: str = "dual"  # legacy, async, dual
    PROGRESS_INDICATORS_ENABLED: bool = True
    MANUAL_REFRESH_ENABLED: bool = True
    
    # N8N integration settings
    N8N_ENABLED: bool = False
    N8N_WEBHOOK_URL: Optional[str] = None  # For detailed backlinks
    N8N_WEBHOOK_URL_SUMMARY: Optional[str] = None  # For summary backlinks
    N8N_WEBHOOK_URL_BULK: Optional[str] = None  # For bulk page summary
    N8N_WEBHOOK_URL_BULK_RANK: Optional[str] = None  # For bulk rank
    N8N_WEBHOOK_URL_BULK_BACKLINKS: Optional[str] = None  # For bulk backlinks
    N8N_WEBHOOK_URL_BULK_SPAM_SCORE: Optional[str] = None  # For bulk spam score
    N8N_WEBHOOK_URL_BULK_TRAFFIC: Optional[str] = None  # For bulk traffic
    N8N_WEBHOOK_URL_TRUNCATE: Optional[str] = None  # For truncating tables via SQL
    N8N_WEBHOOK_URL_AUCTION_SCORING: Optional[str] = None  # For auction scoring workflow
    N8N_CALLBACK_URL: Optional[str] = None
    N8N_TIMEOUT: int = 60  # seconds
    N8N_USE_FOR_BACKLINKS: bool = True
    N8N_USE_FOR_SUMMARY: bool = True  # Use N8N for summary backlinks
    
    # Domain scoring settings
    TIER_1_TLDS: List[str] = ['.com', '.net', '.org', '.co', '.io', '.ai']
    MAX_DOMAIN_LENGTH: int = 15  # characters (excluding TLD)
    MAX_NUMBERS: int = 2
    MIN_WORD_RECOGNITION_RATIO: float = 0.5  # 50%
    TOP_DOMAINS_FOR_ANALYSIS: int = 1000
    TOP_RANK_THRESHOLD: int = 3000
    SCORING_CACHE_TTL_HOURS: int = 1
    
    # Security settings
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables (like REACT_APP_*)
        # Force reading from .env file even if env var is set (by using env_file_encoding)
        # Note: pydantic-settings prioritizes env vars, but we want .env to be the source of truth


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (singleton pattern)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings():
    """Reset settings cache (useful for testing or when env vars change)"""
    global _settings
    _settings = None


def validate_required_settings():
    """Validate that all required settings are present"""
    settings = get_settings()
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_KEY", 
        "SECRET_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var, None):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return True
