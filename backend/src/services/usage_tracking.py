"""
Service for tracking user resource consumption
"""

import structlog
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

from services.database import get_database

logger = structlog.get_logger()

class UsageTrackingService:
    """Service to track resource usage by users"""
    
    def __init__(self):
        self._db = None
        
    @property
    def db(self):
        if self._db is None:
            self._db = get_database()
        return self._db
        
    async def track_usage(
        self,
        user_id: Optional[UUID],
        resource_type: str,
        operation: str,
        provider: str,
        model: Optional[str] = None,
        tokens_input: int = 0,
        tokens_output: int = 0,
        cost_estimated: float = 0.0,
        details: Dict[str, Any] = None
    ) -> bool:
        """
        Track usage of a resource
        
        Args:
            user_id: UUID of the user (can be None for system operations, but should be provided)
            resource_type: Type of resource ('llm', 'dataforseo', etc.)
            operation: Specific operation ('analyze_domain', 'backlinks', etc.)
            provider: Service provider ('openai', 'gemini', 'dataforseo')
            model: Model name if applicable
            tokens_input: Input tokens/units
            tokens_output: Output tokens/units
            cost_estimated: Estimated cost
            details: Additional details
            
        Returns:
            bool: True if tracked successfully
        """
        try:
            if not details:
                details = {}
                
            # Prepare record
            usage_record = {
                'user_id': str(user_id) if user_id else None,
                'resource_type': resource_type,
                'operation': operation,
                'provider': provider,
                'model': model,
                'tokens_input': tokens_input,
                'tokens_output': tokens_output,
                'cost_estimated': cost_estimated,
                'details': details,
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Use Supabase client directly
            if self.db.client:
                self.db.client.table('user_resource_usage').insert(usage_record).execute()
                logger.info("Usage tracked", 
                           user_id=str(user_id) if user_id else "system",
                           resource=resource_type,
                           operation=operation)
                return True
            else:
                logger.warning("Database client not available for usage tracking")
                return False
                
        except Exception as e:
            logger.error("Failed to track usage", error=str(e), operation=operation)
            # Don't raise exception to avoid blocking the main operation
            return False
