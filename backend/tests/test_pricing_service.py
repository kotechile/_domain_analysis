
import unittest
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.pricing_service import PricingService

class TestPricingService(unittest.TestCase):
    def setUp(self):
        self.pricing_service = PricingService()

    def test_calculate_cost_dataforseo(self):
        # Base cost 0.05 * 2.0 multiplier = 0.10
        cost = self.pricing_service.calculate_cost(
            resource_type='dataforseo',
            provider='dataforseo',
            details={'operation': 'domain_analytics'}
        )
        self.assertAlmostEqual(cost, 0.10)

    def test_calculate_cost_llm_openai(self):
        # gpt-4o: input 0.005, output 0.015 per 1k tokens
        # 1000 input tokens = 0.005
        # 1000 output tokens = 0.015
        # Total base = 0.020
        # Multiplier 2.0 -> Total 0.040
        cost = self.pricing_service.calculate_cost(
            resource_type='llm',
            provider='openai',
            model='gpt-4o',
            tokens_input=1000,
            tokens_output=1000
        )
        self.assertAlmostEqual(cost, 0.040)

    def test_calculate_cost_llm_gemini(self):
        # gemini-1.5-flash: input 0.00035, output 0.00105 per 1k tokens
        # 1M input tokens = 0.35
        # 1M output tokens = 1.05
        # Total base = 1.40
        # Multiplier 2.0 -> Total 2.80
        cost = self.pricing_service.calculate_cost(
            resource_type='llm',
            provider='gemini',
            model='gemini-1.5-flash',
            tokens_input=1000000,
            tokens_output=1000000
        )
        self.assertAlmostEqual(cost, 2.80)

if __name__ == '__main__':
    unittest.main()
