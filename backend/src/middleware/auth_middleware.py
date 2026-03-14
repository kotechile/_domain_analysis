"""
Authentication Middleware
Validates Supabase JWT tokens
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.database import get_database
import structlog

logger = structlog.get_logger()
security = HTTPBearer()

from typing import Optional
from uuid import UUID

class MockUser:
    def __init__(self, id, email):
        self.id = UUID(id)
        self.email = email

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    """
    Validate the Supabase JWT token and return the user.
    If no credentials are provided, return a fallback user for local development.
    """
    if not credentials:
        # Fallback for local development testing
        logger.warning("No authentication provided, using fallback developer account")
        return MockUser(
            id="942d09c0-58ce-4fe5-b412-f16ac1694a72", 
            email="jorge.fernandez@kotechile.cl"
        )

    token = credentials.credentials
    
    try:
        db_service = get_database()
        if not db_service.client:
            logger.error("Supabase client not initialized")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service unavailable"
            )
            
        # Verify token with Supabase
        user_response = db_service.client.auth.get_user(token)
        
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return user_response.user
        
    except Exception as e:
        logger.error("Authentication failed", error=str(e))
        # Even on error, if we're in dev, we could fallback, but let's just do it for missing credentials.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

