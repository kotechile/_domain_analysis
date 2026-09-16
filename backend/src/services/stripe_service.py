import stripe
import structlog
from typing import Optional, Dict, Any
from uuid import UUID
from services.database import get_database
from services.credits_service import CreditsService
from utils.config import get_settings

logger = structlog.get_logger()


class StripeService:
    """Service for handling Stripe payment integration"""

    def __init__(self):
        settings = get_settings()
        self._secret_key = settings.STRIPE_SECRET_KEY
        self._webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        if self._secret_key:
            stripe.api_key = self._secret_key
        self._price_ids = {
            'pro': settings.STRIPE_PRO_PRICE_ID,
            'agency': settings.STRIPE_AGENCY_PRICE_ID,
            'credit_pack_small': settings.STRIPE_CREDIT_PACK_SMALL_PRICE_ID,
            'credit_pack_medium': settings.STRIPE_CREDIT_PACK_MEDIUM_PRICE_ID,
            'credit_pack_large': settings.STRIPE_CREDIT_PACK_LARGE_PRICE_ID,
        }

    @property
    def is_configured(self) -> bool:
        return bool(self._secret_key)

    def get_publishable_key(self) -> Optional[str]:
        return get_settings().STRIPE_PUBLISHABLE_KEY

    async def create_checkout_session(
        self,
        user_id: str,
        price_id: str,
        mode: str = 'payment',
        quantity: int = 1,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout Session for credit purchases or subscriptions."""
        if not self.is_configured:
            raise RuntimeError("Stripe is not configured. Set STRIPE_SECRET_KEY.")

        try:
            session_params: Dict[str, Any] = {
                'client_reference_id': str(user_id),
                'mode': mode,
                'line_items': [{
                    'price': price_id,
                    'quantity': quantity,
                }],
                'payment_method_types': ['card'],
            }

            if success_url:
                session_params['success_url'] = success_url
            else:
                session_params['success_url'] = 'https://scout.buildomain.com/app/billing?session_id={CHECKOUT_SESSION_ID}'

            if cancel_url:
                session_params['cancel_url'] = cancel_url
            else:
                session_params['cancel_url'] = 'https://scout.buildomain.com/app/billing'

            session = stripe.checkout.Session.create(**session_params)
            logger.info("Stripe checkout session created", session_id=session.id, user_id=user_id)
            return {
                'session_id': session.id,
                'url': session.url,
            }
        except stripe.error.StripeError as e:
            logger.error("Failed to create Stripe checkout session", user_id=user_id, error=str(e))
            raise

    async def create_customer_portal_session(
        self,
        stripe_customer_id: str,
        return_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a Stripe Customer Portal session for managing subscriptions."""
        if not self.is_configured:
            raise RuntimeError("Stripe is not configured.")

        try:
            session = stripe.billing_portal.Session.create(
                customer=stripe_customer_id,
                return_url=return_url or 'https://scout.buildomain.com/app/billing',
            )
            return {'url': session.url}
        except stripe.error.StripeError as e:
            logger.error("Failed to create customer portal session", error=str(e))
            raise

    async def handle_webhook_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming Stripe webhook events and update credits/subscriptions."""
        event_type = event.get('type')
        logger.info("Processing Stripe webhook", event_type=event_type)

        if event_type == 'checkout.session.completed':
            return await self._handle_checkout_completed(event)
        elif event_type == 'invoice.paid':
            return await self._handle_invoice_paid(event)
        elif event_type == 'customer.subscription.updated':
            return await self._handle_subscription_updated(event)
        elif event_type == 'customer.subscription.deleted':
            return await self._handle_subscription_deleted(event)
        else:
            logger.info("Unhandled Stripe event type", event_type=event_type)
            return {'status': 'ignored', 'event_type': event_type}

    async def _handle_checkout_completed(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle completed checkout sessions - grant credits or activate subscription."""
        session = event['data']['object']
        user_id = session.get('client_reference_id')
        mode = session.get('mode')

        if not user_id:
            logger.error("No client_reference_id in checkout session", session_id=session.get('id'))
            return {'status': 'error', 'error': 'missing_client_reference_id'}

        db = get_database()
        credits_service = CreditsService(db)

        if mode == 'payment':
            amount_total = session.get('amount_total', 0)
            credits_to_add = self._calculate_credits_from_amount(amount_total)
            reference_id = session.get('payment_intent') or session.get('id', 'stripe_unknown')

            new_balance = await credits_service.add_credits(
                user_id=UUID(user_id),
                amount=credits_to_add,
                description=f"Credit purchase via Stripe (${amount_total / 100:.2f})",
                reference_id=f"stripe_{reference_id}",
                dollar_amount=amount_total / 100.0,
            )

            logger.info("Credits granted via Stripe checkout",
                         user_id=user_id,
                         credits=credits_to_add,
                         new_balance=new_balance)

            return {'status': 'success', 'credits_added': credits_to_add, 'new_balance': new_balance}

        elif mode == 'subscription':
            subscription_id = session.get('subscription')
            logger.info("Subscription checkout completed",
                        user_id=user_id,
                        subscription_id=subscription_id)
            return {'status': 'success', 'subscription_id': subscription_id}

        return {'status': 'unknown_mode', 'mode': mode}

    async def _handle_invoice_paid(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle recurring subscription invoice payments - grant monthly credits."""
        invoice = event['data']['object']
        customer_id = invoice.get('customer')
        subscription_id = invoice.get('subscription')
        amount_paid = invoice.get('amount_paid', 0) or invoice.get('total', 0)

        db = get_database()
        client = await db._get_client()

        user_id = None
        try:
            result = await client.table('user_subscriptions').select('user_id').eq('stripe_customer_id', customer_id).execute()
            if result.data:
                user_id = result.data[0]['user_id']
        except Exception:
            pass

        if not user_id:
            logger.error("Could not find user for Stripe customer", customer_id=customer_id)
            return {'status': 'error', 'error': 'user_not_found'}

        price_id = None
        lines = invoice.get('lines', {}).get('data', [])
        if lines:
            price_id = lines[0].get('price', {}).get('id')

        monthly_credits = self._get_subscription_credits(price_id)

        credits_service = CreditsService(db)
        new_balance = await credits_service.add_credits(
            user_id=UUID(user_id),
            amount=monthly_credits,
            description=f"Monthly subscription credits (invoice {invoice.get('id', 'unknown')})",
            reference_id=f"stripe_invoice_{invoice.get('id', 'unknown')}",
            dollar_amount=amount_paid / 100.0,
        )

        logger.info("Monthly credits granted via subscription invoice",
                     user_id=user_id,
                     credits=monthly_credits,
                     new_balance=new_balance)

        return {'status': 'success', 'credits_added': monthly_credits, 'new_balance': new_balance}

    async def _handle_subscription_updated(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription updates - change tier."""
        subscription = event['data']['object']
        logger.info("Subscription updated", subscription_id=subscription.get('id'))
        return {'status': 'success'}

    async def _handle_subscription_deleted(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle subscription cancellation."""
        subscription = event['data']['object']
        logger.info("Subscription cancelled", subscription_id=subscription.get('id'))
        return {'status': 'success'}

    def _calculate_credits_from_amount(self, amount_cents: int) -> float:
        """Calculate credits from Stripe payment amount.

        Pricing model:
        - $5  -> 50 credits (Starter Pack)
        - $20 -> 250 credits (Pro Bundle)
        - $75 -> 1000 credits (Enterprise Scout)
        """
        dollar_amount = amount_cents / 100.0
        if dollar_amount <= 0:
            return 0.0

        credit_packs = [
            (75.00, 1000.0),
            (20.00, 250.0),
            (5.00, 50.0),
        ]
        for price, credits in credit_packs:
            if abs(dollar_amount - price) < 0.50:
                return credits

        return round(dollar_amount * 10.0, 2)

    def _get_subscription_credits(self, price_id: Optional[str]) -> float:
        """Return monthly credit allowance for a subscription price tier.

        - Pro ($19/mo) -> 200 credits/mo
        - Agency ($49/mo) -> unlimited=9999 credits/mo
        """
        settings = get_settings()
        if price_id == settings.STRIPE_PRO_PRICE_ID:
            return 200.0
        elif price_id == settings.STRIPE_AGENCY_PRICE_ID:
            return 9999.0
        return 100.0

    def get_available_plans(self) -> Dict[str, Any]:
        """Return available pricing plans for the frontend."""
        return {
            'publishable_key': self.get_publishable_key(),
            'credit_packs': [
                {
                    'id': 'credit_pack_small',
                    'name': 'Starter Pack',
                    'credits': 50,
                    'price_cents': 500,
                    'price_id': self._price_ids.get('credit_pack_small'),
                },
                {
                    'id': 'credit_pack_medium',
                    'name': 'Pro Bundle',
                    'credits': 250,
                    'price_cents': 2000,
                    'price_id': self._price_ids.get('credit_pack_medium'),
                    'popular': True,
                },
                {
                    'id': 'credit_pack_large',
                    'name': 'Enterprise Scout',
                    'credits': 1000,
                    'price_cents': 7500,
                    'price_id': self._price_ids.get('credit_pack_large'),
                },
            ],
            'subscriptions': [
                {
                    'id': 'pro',
                    'name': 'Pro',
                    'monthly_price_cents': 1900,
                    'monthly_credits': 200,
                    'price_id': self._price_ids.get('pro'),
                },
                {
                    'id': 'agency',
                    'name': 'Agency',
                    'monthly_price_cents': 4900,
                    'monthly_credits': 9999,
                    'price_id': self._price_ids.get('agency'),
                },
            ],
        }