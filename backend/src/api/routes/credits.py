
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
import structlog
from datetime import datetime

from middleware.auth_middleware import get_current_user
from services.database import get_database
from services.credits_service import CreditsService

logger = structlog.get_logger()
router = APIRouter()

# Response models
class BalanceResponse(BaseModel):
    user_id: str
    balance: float
    currency: str = "USD"

class TransactionResponse(BaseModel):
    id: str
    amount: float
    transaction_type: str
    description: str
    reference_id: Optional[str]
    balance_after: float
    created_at: str

class PurchaseRequest(BaseModel):
    amount: float
    description: str = "Credit purchase"
    reference_id: Optional[str] = None

class PurchaseResponse(BaseModel):
    success: bool
    new_balance: float
    message: str


@router.get("/credits/balance", response_model=BalanceResponse)
async def get_balance(current_user = Depends(get_current_user)):
    """Get current user's credit balance"""
    try:
        db = get_database()
        credits_service = CreditsService(db)
        
        balance = await credits_service.get_balance(current_user.id)
        
        return BalanceResponse(
            user_id=str(current_user.id),
            balance=balance
        )
    except Exception as e:
        logger.error("Failed to get balance", user_id=str(current_user.id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve balance")

@router.get("/credits/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    limit: int = 20, 
    offset: int = 0, 
    current_user = Depends(get_current_user)
):
    """Get user's transaction history"""
    try:
        db = get_database()
        credits_service = CreditsService(db)
        
        transactions = await credits_service.get_transactions(current_user.id, limit, offset)
        
        # Format response
        result = []
        for t in transactions:
            result.append(TransactionResponse(
                id=t['id'],
                amount=float(t['amount']),
                transaction_type=t['transaction_type'],
                description=t.get('description', ''),
                reference_id=t.get('reference_id'),
                balance_after=float(t['balance_after']),
                created_at=t['created_at']
            ))
            
        return result
    except Exception as e:
        logger.error("Failed to get transactions", user_id=str(current_user.id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve transactions")

# Internal/Admin endpoint for adding credits (Mocking purchase flow)
# In production, this would be a webhook from Stripe/LemonSqueezy
@router.post("/credits/purchase", response_model=PurchaseResponse)
async def purchase_credits(
    request: PurchaseRequest,
    current_user = Depends(get_current_user)
):
    """
    Simulate a credit purchase.
    In a real app, this would be handled via payment gateway webhooks.
    """
    try:
        if request.amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")
            
        db = get_database()
        credits_service = CreditsService(db)
        
        # Generate a reference ID if not provided
        ref_id = request.reference_id or f"purchase_{int(datetime.utcnow().timestamp())}"
        
        new_balance = await credits_service.add_credits(
            user_id=current_user.id,
            amount=request.amount,
            description=request.description,
            reference_id=ref_id
        )
        
        return PurchaseResponse(
            success=True,
            new_balance=new_balance,
            message="Credits added successfully"
        )
    except Exception as e:
        logger.error("Failed to purchase credits", user_id=str(current_user.id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process purchase")
