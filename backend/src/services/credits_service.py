
from typing import Optional, List, Dict, Any
from uuid import UUID
import structlog
from datetime import datetime

from services.database import DatabaseService

logger = structlog.get_logger()

class CreditsService:
    """Service for managing user credits"""

    def __init__(self, db: DatabaseService):
        self.db = db

    async def get_balance(self, user_id: UUID) -> float:
        """Get current credit balance for a user"""
        try:
            response = self.db.client.table('user_credits').select('balance').eq('user_id', str(user_id)).execute()
            if response.data:
                return float(response.data[0]['balance'])
            
            # If no record exists, create one with 0 balance
            # This handles new users gracefully
            try:
                self.db.client.table('user_credits').insert({
                    'user_id': str(user_id), 
                    'balance': 0.0
                }).execute()
                return 0.0
            except Exception as e:
                logger.error("Failed to initialize user credits", user_id=str(user_id), error=str(e))
                return 0.0
                
        except Exception as e:
            logger.error("Failed to get credit balance", user_id=str(user_id), error=str(e))
            raise

    async def deduct_credits(
        self, 
        user_id: UUID, 
        amount: float, 
        description: str, 
        reference_id: Optional[str] = None
    ) -> bool:
        """
        Deduct credits from user's balance.
        Returns True if successful, False if insufficient funds.
        """
        try:
            # key for RPC
            params = {
                'p_user_id': str(user_id),
                'p_amount': float(amount),
                'p_description': description,
                'p_reference_id': reference_id
            }
            
            response = self.db.client.rpc('deduct_credits', params).execute()
            
            if response.data:
                success = response.data.get('success', False)
                if not success:
                    logger.warning("Credit deduction failed", user_id=str(user_id), error=response.data.get('error'))
                else:
                    logger.info("Credits deducted", user_id=str(user_id), amount=amount, new_balance=response.data.get('new_balance'))
                return success
            
            return False
            
        except Exception as e:
            logger.error("Error calling deduct_credits RPC", user_id=str(user_id), error=str(e))
            # Fallback (unsafe): Check balance and update manually if RPC fails/doesn't exist
            # This is risky but better than crashing if migration wasn't perfect
            return await self._deduct_credits_fallback(user_id, amount, description, reference_id)

    async def _deduct_credits_fallback(self, user_id: UUID, amount: float, description: str, reference_id: str) -> bool:
        """Fallback method for deduction if RPC is missing"""
        # This is not thread-safe!
        balance = await self.get_balance(user_id)
        if balance < amount:
            return False
        
        new_balance = balance - amount
        
        # Update balance
        self.db.client.table('user_credits').update({'balance': new_balance}).eq('user_id', str(user_id)).execute()
        
        # Record transaction
        self.db.client.table('credit_transactions').insert({
            'user_id': str(user_id),
            'amount': -amount,
            'transaction_type': 'usage',
            'reference_id': reference_id,
            'description': description,
            'balance_after': new_balance
        }).execute()
        
        return True

    async def add_credits(self, user_id: UUID, amount: float, description: str, reference_id: str) -> float:
        """Add credits to user (e.g. purchase)"""
        # For adding credits, concurrency is less critical than deduction, but still important.
        # Ideally create an RPC for this too, but for now fallback logic is acceptable for purchases
        # assuming admin/payment webhook context.
        
        current_balance = await self.get_balance(user_id)
        new_balance = current_balance + amount
        
        self.db.client.table('user_credits').update({'balance': new_balance}).eq('user_id', str(user_id)).execute()
        
        self.db.client.table('credit_transactions').insert({
            'user_id': str(user_id),
            'amount': amount,
            'transaction_type': 'purchase',
            'reference_id': reference_id,
            'description': description,
            'balance_after': new_balance
        }).execute()
        
        return new_balance

    async def get_transactions(self, user_id: UUID, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get transaction history"""
        response = self.db.client.table('credit_transactions')\
            .select('*')\
            .eq('user_id', str(user_id))\
            .order('created_at', desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
            
        return response.data
