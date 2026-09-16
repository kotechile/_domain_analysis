from fastapi import APIRouter, HTTPException, Depends, Request, Header
from typing import List, Optional
from pydantic import BaseModel
import structlog
from datetime import datetime

from middleware.auth_middleware import get_current_user
from services.database import get_database
from services.credits_service import CreditsService
from services.stripe_service import StripeService
from utils.config import get_settings

logger = structlog.get_logger()
router = APIRouter()


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
    dollar_amount: float = 0.0
    created_at: str


class PurchaseRequest(BaseModel):
    amount: float
    description: str = "Credit purchase"
    reference_id: Optional[str] = None


class PurchaseResponse(BaseModel):
    success: bool
    new_balance: float
    message: str


class CheckoutRequest(BaseModel):
    price_id: str
    mode: str = "payment"
    quantity: int = 1
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutResponse(BaseModel):
    session_id: str
    url: str


class PlansResponse(BaseModel):
    publishable_key: Optional[str] = None
    credit_packs: list = []
    subscriptions: list = []


@router.get("/credits/balance", response_model=BalanceResponse)
async def get_balance(current_user=Depends(get_current_user)):
    """Get current user's credit balance"""
    try:
        db = get_database()
        credits_service = CreditsService(db)

        await credits_service.check_and_reset_monthly_credits(current_user.id)

        balance = await credits_service.get_balance(current_user.id)

        return BalanceResponse(user_id=str(current_user.id), balance=balance)
    except Exception as e:
        logger.error("Failed to get balance", user_id=str(current_user.id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve balance")


@router.get("/credits/transactions", response_model=List[TransactionResponse])
async def get_transactions(limit: int = 20, offset: int = 0, current_user=Depends(get_current_user)):
    """Get user's transaction history"""
    try:
        db = get_database()
        credits_service = CreditsService(db)

        transactions = await credits_service.get_transactions(current_user.id, limit, offset)

        result = []
        for t in transactions:
            result.append(TransactionResponse(
                id=t['id'],
                amount=float(t['amount']),
                transaction_type=t['transaction_type'],
                description=t.get('description', ''),
                reference_id=t.get('reference_id'),
                balance_after=float(t['balance_after']),
                dollar_amount=float(t.get('dollar_amount', 0.0)),
                created_at=t['created_at']
            ))

        return result
    except Exception as e:
        logger.error("Failed to get transactions", user_id=str(current_user.id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve transactions")


@router.get("/credits/payments", response_model=List[TransactionResponse])
async def get_payments(limit: int = 20, offset: int = 0, current_user=Depends(get_current_user)):
    """Get user's payment history (only positive additions)"""
    try:
        db = get_database()
        credits_service = CreditsService(db)

        transactions = await credits_service.get_transactions(current_user.id, limit=100, offset=0)

        payments = [t for t in transactions if t.get('transaction_type') in ['purchase', 'admin_add'] or t.get('amount', 0) > 0]

        paged_payments = payments[offset:offset + limit]

        result = []
        for t in paged_payments:
            result.append(TransactionResponse(
                id=t['id'],
                amount=float(t['amount']),
                transaction_type=t['transaction_type'],
                description=t.get('description', ''),
                reference_id=t.get('reference_id'),
                balance_after=float(t['balance_after']),
                dollar_amount=float(t.get('dollar_amount', 0.0)),
                created_at=t['created_at']
            ))

        return result
    except Exception as e:
        logger.error("Failed to get payments", user_id=str(current_user.id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve payment history")


@router.post("/credits/purchase", response_model=PurchaseResponse)
async def purchase_credits(request: PurchaseRequest, current_user=Depends(get_current_user)):
    """
    Direct credit purchases are disabled. Use Stripe Checkout via /credits/checkout instead.
    """
    raise HTTPException(
        status_code=501,
        detail="Direct purchases are disabled. Use the Stripe checkout flow at /api/v1/credits/checkout."
    )


@router.get("/credits/plans", response_model=PlansResponse)
async def get_plans():
    """Get available pricing plans and Stripe publishable key for the frontend."""
    stripe_service = StripeService()
    plans = stripe_service.get_available_plans()
    return PlansResponse(**plans)


@router.post("/credits/checkout", response_model=CheckoutResponse)
async def create_checkout_session(request: CheckoutRequest, current_user=Depends(get_current_user)):
    """Create a Stripe Checkout Session for purchasing credits or subscribing to a plan."""
    stripe_service = StripeService()

    if not stripe_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Stripe payment integration is not configured. Please set STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY."
        )

    try:
        result = await stripe_service.create_checkout_session(
            user_id=str(current_user.id),
            price_id=request.price_id,
            mode=request.mode,
            quantity=request.quantity,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )
        return CheckoutResponse(session_id=result['session_id'], url=result['url'])
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error("Failed to create checkout session", user_id=str(current_user.id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """
    Secure webhook for Stripe events (e.g., checkout.session.completed).
    Verifies Stripe signature before processing.
    """
    stripe_service = StripeService()

    if not stripe_service.is_configured:
        logger.warning("Stripe webhook received but Stripe is not configured")
        return {"status": "ignored", "message": "Stripe not configured"}

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        logger.warning("Stripe webhook missing signature header")
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    settings = get_settings()
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not set - cannot verify webhook signatures")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    import stripe as stripe_lib
    try:
        event = stripe_lib.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except stripe_lib.error.SignatureVerificationError as e:
        logger.error("Stripe webhook signature verification failed", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error("Stripe webhook event construction failed", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid payload")

    try:
        result = await stripe_service.handle_webhook_event(event)
        return result
    except Exception as e:
        logger.error("Failed to handle Stripe webhook event", event_type=event.get('type'), error=str(e))
        raise HTTPException(status_code=500, detail="Webhook processing failed")