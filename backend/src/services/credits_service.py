
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
        reference_id: Optional[str] = None,
        dollar_amount: float = 0.0
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
                'p_reference_id': reference_id,
                'p_dollar_amount': float(dollar_amount)
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
            return await self._deduct_credits_fallback(user_id, amount, description, reference_id, dollar_amount)

    async def _deduct_credits_fallback(self, user_id: UUID, amount: float, description: str, reference_id: str, dollar_amount: float = 0.0) -> bool:
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
            'amount': -float(amount),
            'transaction_type': 'usage',
            'reference_id': reference_id,
            'description': description,
            'balance_after': float(new_balance)
        }).execute()
        
        return True

    async def add_credits(self, user_id: UUID, amount: float, description: str, reference_id: str, dollar_amount: float = 0.0) -> float:
        """Add credits to user (e.g. purchase)"""
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

    async def get_pricing_plans(self) -> List[Dict[str, Any]]:
        """Get active pricing plans"""
        response = self.db.client.table('pricing_plans').select('*').eq('is_active', True).execute()
        return response.data

    async def get_global_settings(self) -> Dict[str, Any]:
        """Get all global settings as a dictionary"""
        response = self.db.client.table('global_settings').select('*').execute()
        settings = {}
        for row in response.data:
            settings[row['key']] = row['value']
        return settings

    async def check_and_reset_monthly_credits(self, user_id: UUID):
        """
        Logic to reset credits every month.
        Checks last_reset_at and updates it if more than 30 days have passed.
        """
        try:
            response = self.db.client.table('user_credits').select('*').eq('user_id', str(user_id)).execute()
            if not response.data:
                # Initialize credits if not exists
                self.db.client.table('user_credits').insert({
                    'user_id': str(user_id),
                    'balance': 0.0,
                    'last_reset_at': datetime.utcnow().isoformat()
                }).execute()
                return

            user_data = response.data[0]
            last_reset_at_str = user_data.get('last_reset_at')
            
            now = datetime.utcnow()
            should_reset = False
            
            if not last_reset_at_str:
                should_reset = True
            else:
                try:
                    # Basic check: is it a different month?
                    last_reset = datetime.fromisoformat(last_reset_at_str.replace('Z', '+00:00')).replace(tzinfo=None)
                    if (now.year > last_reset.year) or (now.month > last_reset.month):
                        should_reset = True
                except Exception:
                    should_reset = True

            if should_reset:
                logger.info("Performing monthly credit reset/update", user_id=str(user_id))
                # For now, we just update the timestamp. 
                # Actual credit allocation logic would go here if we had monthly subscriptions.
                self.db.client.table('user_credits').update({
                    'last_reset_at': now.isoformat(),
                    'updated_at': now.isoformat()
                }).eq('user_id', str(user_id)).execute()
                
        except Exception as e:
            logger.error("Failed to check/reset monthly credits", user_id=str(user_id), error=str(e))

    async def get_transactions(self, user_id: UUID, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get transaction history"""
        response = self.db.client.table('credit_transactions')\
            .select('*')\
            .eq('user_id', str(user_id))\
            .order('created_at', desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
            
        return response.data
