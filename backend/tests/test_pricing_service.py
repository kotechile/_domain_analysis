
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch
import sys
import os

# Add backend/src to path
sys.path.append(os.path.join(os.getcwd(), 'backend', 'src'))

from services.pricing_service import PricingService

class TestPricingService(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.pricing_service = PricingService()
        # Mock DB client to return default values or empty to use fallbacks
        self.pricing_service._db = MagicMock()
        self.pricing_service._db.client = MagicMock()
        
        # Mock settings response for multiplier
        multiplier_mock = MagicMock()
        multiplier_mock.data = [{'value': '2.0'}]
        self.pricing_service._db.client.table().select().eq().execute.return_value = multiplier_mock
        
        # Mock rates response
        rates_mock = MagicMock()
        rates_mock.data = [
            {'resource_type': 'dataforseo', 'provider': 'dataforseo', 'model': 'domain_analytics', 'input_cost': 0.05, 'output_cost': 0.0},
            {'resource_type': 'llm', 'provider': 'openai', 'model': 'gpt-4o', 'input_cost': 0.005, 'output_cost': 0.015},
            {'resource_type': 'llm', 'provider': 'gemini', 'model': 'gemini-1.5-flash', 'input_cost': 0.00035, 'output_cost': 0.00105}
        ]
        # This is a bit complex due to multiple table() calls, so let's just bypass refresh in some tests or mock it properly
        with patch.object(PricingService, '_refresh_config_if_needed', return_value=None):
            # Manually set cache for testing
            self.pricing_service._rates_cache = {
                'dataforseo': {'dataforseo': {'domain_analytics': {'input': 0.05, 'output': 0.0}}},
                'llm': {
                    'openai': {'gpt-4o': {'input': 0.005, 'output': 0.015}},
                    'gemini': {'gemini-1.5-flash': {'input': 0.00035, 'output': 0.00105}}
                }
            }
            self.pricing_service._multiplier_cache = 2.0
            self.pricing_service._last_refresh = datetime.utcnow()

    async def test_calculate_cost_dataforseo(self):
        # Base cost 0.05 * 2.0 multiplier = 0.10
        cost = await self.pricing_service.calculate_cost(
            resource_type='dataforseo',
            provider='dataforseo',
            details={'operation': 'domain_analytics'}
        )
        self.assertAlmostEqual(cost, 0.10)

    async def test_calculate_cost_llm_openai(self):
        # gpt-4o: input 0.005, output 0.015 per 1k tokens
        # 1000 input tokens = 0.005
        # 1000 output tokens = 0.015
        # Total base = 0.020
        # Multiplier 2.0 -> Total 0.040
        cost = await self.pricing_service.calculate_cost(
            resource_type='llm',
            provider='openai',
            model='gpt-4o',
            tokens_input=1000,
            tokens_output=1000
        )
        self.assertAlmostEqual(cost, 0.040)

    async def test_calculate_cost_llm_gemini(self):
        # gemini-1.5-flash: input 0.00035, output 0.00105 per 1k tokens
        # 1M input tokens = 0.35
        # 1M output tokens = 1.05
        # Total base = 1.40
        # Multiplier 2.0 -> Total 2.80
        cost = await self.pricing_service.calculate_cost(
            resource_type='llm',
            provider='gemini',
            model='gemini-1.5-flash',
            tokens_input=1000000,
            tokens_output=1000000
        )
        self.assertAlmostEqual(cost, 2.80)

if __name__ == '__main__':
    unittest.main()
