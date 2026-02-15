
from typing import Optional, Dict, Any

class PricingService:
    """Service for calculating costs of resource usage"""

    # Base costs (USD)
    # Applying 2x multiplier rule here by defining base cost and multiplier
    COST_MULTIPLIER = 2.0

    # DataForSEO costs (per request)
    DATAFORSEO_COSTS = {
        'domain_analytics': 0.05,
        'backlinks': 0.05,
        'keywords': 0.02
    }

    # LLM costs (per 1k tokens) - approximate
    LLM_COSTS = {
        'openai': {
            'gpt-4o': {'input': 0.005, 'output': 0.015},
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
            'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015}
        },
        'gemini': {
            'gemini-1.5-pro': {'input': 0.0035, 'output': 0.0105},
            'gemini-1.5-flash': {'input': 0.00035, 'output': 0.00105}
        }
    }

    def calculate_cost(
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
        base_cost = 0.0

        if resource_type == 'dataforseo':
            operation = details.get('operation', 'domain_analytics') if details else 'domain_analytics'
            # Map operation to cost key
            cost_key = 'domain_analytics' # Default
            if 'backlinks' in operation:
                cost_key = 'backlinks'
            elif 'keyword' in operation:
                cost_key = 'keywords'
            
            base_cost = self.DATAFORSEO_COSTS.get(cost_key, 0.05)

        elif resource_type == 'llm':
            provider_costs = self.LLM_COSTS.get(provider.lower())
            if provider_costs:
                # Default to a mid-tier model if unknown
                model_costs = provider_costs.get(model, provider_costs.get(list(provider_costs.keys())[0]))
                if model_costs:
                    input_cost = (tokens_input / 1000) * model_costs['input']
                    output_cost = (tokens_output / 1000) * model_costs['output']
                    base_cost = input_cost + output_cost
        
        # Apply multiplier
        total_cost = base_cost * self.COST_MULTIPLIER
        
        # Ensure minimum cost for some operations? 
        # For now, just return calculated cost.
        return round(total_cost, 6)
