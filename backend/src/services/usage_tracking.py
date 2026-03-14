
"""
Service for tracking user resource consumption
"""

import structlog
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

from services.database import get_database
from services.pricing_service import PricingService
from services.credits_service import CreditsService

logger = structlog.get_logger()

class UsageTrackingService:
    """Service to track resource usage by users"""
    
    def __init__(self):
        self._db = None
        self._pricing_service = PricingService()
        self._credits_service = None
        
    @property
    def db(self):
        if self._db is None:
            self._db = get_database()
        return self._db

    @property
    def credits_service(self):
        if self._credits_service is None:
            self._credits_service = CreditsService(self.db)
        return self._credits_service
        
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
            cost_estimated: Estimated cost (if 0, will be calculated)
            details: Additional details
            
        Returns:
            bool: True if tracked successfully
        """
        try:
            if not details:
                details = {}
                
            # Calculate cost if not provided
            if cost_estimated == 0.0:
                cost_estimated = await self._pricing_service.calculate_cost(
                    resource_type=resource_type,
                    provider=provider,
                    model=model,
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    details=details
                )
            
            # Deduct credits if cost > 0 and user is present
            if user_id and cost_estimated > 0:
                try:
                    # Use provided details or generate generic description
                    description = f"Usage: {resource_type} - {operation}"
                    reference_id = details.get('reference_id') or details.get('domain')
                    
                    success = await self.credits_service.deduct_credits(
                        user_id=user_id,
                        amount=cost_estimated,
                        description=description,
                        reference_id=reference_id
                    )
                    
                    if not success:
                        logger.warning("Insufficient credits for usage", user_id=str(user_id), cost=cost_estimated)
                        # Decide if we want to block or just log.
                        # For now, we just log and still record usage (maybe negative balance allowed or just tracked)
                        # Ideally, the operation should fail, but since track_usage is often async/after-fact,
                        # we can't easily roll back external API calls here.
                except Exception as e:
                    logger.error("Failed to deduct credits", error=str(e))

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
                           cost=cost_estimated)
                return True
            else:
                logger.warning("Database client not available for usage tracking")
                return False
                
        except Exception as e:
            logger.error("Failed to track usage", error=str(e), operation=operation)
            # Don't raise exception to avoid blocking the main operation
            return False
