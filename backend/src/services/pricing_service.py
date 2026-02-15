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

            # Fetch multiplier
            settings_resp = self.db.client.table('system_settings').select('value').eq('key', 'cost_multiplier').execute()
            if settings_resp.data:
                try:
                    self._multiplier_cache = float(settings_resp.data[0]['value'])
                except (ValueError, TypeError):
                    logger.error("Invalid cost_multiplier in settings", value=settings_resp.data[0]['value'])

            # Fetch all active rates
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
            
            self._last_refresh = now
            logger.info("Pricing configuration refreshed from database")
        except Exception as e:
            logger.error("Failed to refresh pricing config", error=str(e))
            # Keep existing cache if refresh fails

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
        Applies the configurable multiplier to base costs.
        """
        await self._refresh_config_if_needed()
        
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
        
        # Apply multiplier
        total_cost = base_cost * self._multiplier_cache
        
        return round(total_cost, 6)
