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
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    
    # Database settings (Supabase)
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    
    # External API settings
    DATAFORSEO_LOGIN: str
    DATAFORSEO_PASSWORD: str
    DATAFORSEO_API_URL: str = "https://api.dataforseo.com/v3"
    
    # LLM settings
    GEMINI_API_KEY: str
    OPENAI_API_KEY: Optional[str] = None
    
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
    MAX_BACKLINKS_PER_DOMAIN: int = 100
    
    # Security settings
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (singleton pattern)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def validate_required_settings():
    """Validate that all required settings are present"""
    settings = get_settings()
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_KEY", 
        "DATAFORSEO_LOGIN",
        "DATAFORSEO_PASSWORD",
        "GEMINI_API_KEY",
        "SECRET_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var, None):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return True
