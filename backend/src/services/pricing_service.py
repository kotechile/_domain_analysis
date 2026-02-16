from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import structlog
from services.database import get_database

logger = structlog.get_logger()

class PricingService:
    """Service for calculating costs of resource usage using database config"""

    def __init__(self):
        self._db = None
        self._rates_cache = {}
        self._action_rates_cache = {}
        self._tiers_cache = {}
        self._multiplier_cache = 2.0
        self._last_refresh = None
        self._cache_ttl = timedelta(minutes=5)

    @property
    def db(self):
        if self._db is None:
            self._db = get_database()
        return self._db

    async def _refresh_config_if_needed(self):
        """Refresh pricing configuration from database if cache is expired"""
        now = datetime.utcnow()
        if self._last_refresh and (now - self._last_refresh) < self._cache_ttl:
            return

        try:
            if not self.db or not self.db.client:
                logger.warning("Database client not available, using default pricing")
                return

            # 1. Fetch multiplier
            settings_resp = self.db.client.table('system_settings').select('value').eq('key', 'cost_multiplier').execute()
            if settings_resp.data:
                try:
                    self._multiplier_cache = float(settings_resp.data[0]['value'])
                except (ValueError, TypeError):
                    logger.error("Invalid cost_multiplier in settings", value=settings_resp.data[0]['value'])

            # 2. Fetch all active legacy rates
            rates_resp = self.db.client.table('pricing_rates').select('*').eq('is_active', True).execute()
            if rates_resp.data:
                new_rates = {}
                for rate in rates_resp.data:
                    rtype = rate['resource_type']
                    provider = rate['provider'].lower()
                    model = rate['model']
                    
                    if rtype not in new_rates:
                        new_rates[rtype] = {}
                    if provider not in new_rates[rtype]:
                        new_rates[rtype][provider] = {}
                    
                    new_rates[rtype][provider][model] = {
                        'input': float(rate['input_cost']),
                        'output': float(rate['output_cost'])
                    }
                self._rates_cache = new_rates
            
            # 3. Fetch Action Rates (Tiering System)
            try:
                actions_resp = self.db.client.table('action_rates').select('*').execute()
                if actions_resp.data:
                    self._action_rates_cache = {r['action_name']: r for r in actions_resp.data}
            except Exception as ae:
                logger.warning("action_rates table not available yet", error=str(ae))

            # 4. Fetch Tiers
            try:
                tiers_resp = self.db.client.table('subscription_tiers').select('*').execute()
                if tiers_resp.data:
                    self._tiers_cache = {t['id']: t for t in tiers_resp.data}
            except Exception as te:
                logger.warning("subscription_tiers table not available yet", error=str(te))
            
            self._last_refresh = now
            logger.info("Pricing configuration refreshed from database")
        except Exception as e:
            logger.error("Failed to refresh pricing config", error=str(e))
            # Keep existing cache if refresh fails

    async def calculate_action_cost(self, action_name: str, quantity: float = 1.0) -> float:
        """
        Calculate cost for a specific tiered action.
        Example: calculate_action_cost('stats_sync', 2000) -> 0.16 credits
        """
        await self._refresh_config_if_needed()
        
        action_info = self._action_rates_cache.get(action_name)
        if not action_info:
            logger.warning("Action rate not found, using legacy calculation", action=action_name)
            return 0.0

        base_credit_cost = float(action_info['credit_cost'])
        unit_amount = int(action_info.get('unit_amount', 1))
        
        # Calculate proportional cost based on quantity and unit_amount
        total_cost = (quantity / unit_amount) * base_credit_cost
        
        return round(total_cost, 4)

    async def get_user_subscription(self, user_id: str) -> Dict[str, Any]:
        """Get user's current subscription details"""
        try:
            resp = self.db.client.table('user_subscriptions').select('*, subscription_tiers(*)').eq('user_id', user_id).execute()
            if resp.data:
                return resp.data[0]
            
            # Default to free tier if no subscription record
            await self._refresh_config_if_needed()
            free_tier = self._tiers_cache.get('free', {'name': 'Free Tier', 'id': 'free'})
            return {
                'user_id': user_id,
                'tier_id': 'free',
                'status': 'active',
                'subscription_tiers': free_tier
            }
        except Exception as e:
            logger.error("Failed to get user subscription", user_id=user_id, error=str(e))
            return {'tier_id': 'free', 'status': 'active'}

    async def calculate_cost(
        self,
        resource_type: str,
        provider: str,
        model: Optional[str] = None,
        tokens_input: int = 0,
        tokens_output: int = 0,
        details: Dict[str, Any] = None
    ) -> float:
        """
        Calculate the cost in credits (USD) for a given usage.
        Prioritizes action-based tiering if specified in details.
        """
        await self._refresh_config_if_needed()
        
        # Check if an explicit action is provided (Tiering System)
        if details and 'action' in details:
            action_name = details['action']
            quantity = details.get('quantity', 1.0)
            action_cost = await self.calculate_action_cost(action_name, quantity)
            if action_cost > 0:
                return action_cost

        # Fallback to legacy resource-based calculation
        base_cost = 0.0
        provider = provider.lower()

        if resource_type == 'dataforseo':
            operation = details.get('operation', 'domain_analytics') if details else 'domain_analytics'
            # Map common operation names to model keys used in the DB
            cost_key = 'domain_analytics'
            if 'backlinks' in operation:
                cost_key = 'backlinks'
            elif 'keyword' in operation:
                cost_key = 'keywords'
            
            # Look up in cache
            provider_rates = self._rates_cache.get('dataforseo', {}).get('dataforseo', {})
            rate_info = provider_rates.get(cost_key, provider_rates.get('domain_analytics', {'input': 0.05}))
            base_cost = rate_info['input']

        elif resource_type == 'llm':
            provider_rates = self._rates_cache.get('llm', {}).get(provider)
            if provider_rates:
                # Default to the first available model if specific model not found
                model_costs = provider_rates.get(model, provider_rates.get(list(provider_rates.keys())[0]))
                if model_costs:
                    input_cost = (tokens_input / 1000) * model_costs['input']
                    output_cost = (tokens_output / 1000) * model_costs['output']
                    base_cost = input_cost + output_cost
        
        # Apply multiplier for legacy costs
        total_cost = base_cost * self._multiplier_cache
        
        return round(total_cost, 6)
