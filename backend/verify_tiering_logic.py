import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from services.database import DatabaseService
from services.pricing_service import PricingService

async def verify_pricing_logic():
    print("Testing PricingService Action-Based Logic...")
    
    pricing = PricingService()
    
    # Mock data for action_rates
    mock_action_rates = [
        {'action_name': 'stats_sync', 'credit_cost': 0.08, 'unit_amount': 1000},
        {'action_name': 'ai_domain_summary', 'credit_cost': 0.25, 'unit_amount': 1},
        {'action_name': 'deep_content_analysis', 'credit_cost': 1.00, 'unit_amount': 1}
    ]
    
    # Mock data for tiers
    mock_tiers = [
        {'id': 'free', 'name': 'Free Tier', 'monthly_price': 0, 'included_credits': 5},
        {'id': 'pro', 'name': 'Pro Tier', 'monthly_price': 29, 'included_credits': 100}
    ]
    
    # Patch the DatabaseService instance
    with patch('services.pricing_service.get_database') as mock_get_db:
        mock_db = MagicMock()
        mock_client = MagicMock()
        mock_db.client = mock_client
        mock_get_db.return_value = mock_db
        
        # Mock responses for different tables
        def side_effect(table_name):
            mock_table = MagicMock()
            if table_name == 'system_settings':
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [{'value': '2.0'}]
            elif table_name == 'pricing_rates':
                mock_table.select.return_value.eq.return_value.execute.return_value.data = []
            elif table_name == 'action_rates':
                mock_table.select.return_value.execute.return_value.data = mock_action_rates
            elif table_name == 'subscription_tiers':
                mock_table.select.return_value.execute.return_value.data = mock_tiers
            elif table_name == 'user_subscriptions':
                mock_table.select.return_value.eq.return_value.execute.return_value.data = []
            return mock_table
            
        mock_client.table.side_effect = side_effect
        
        # Test 1: Action-based cost for AI Domain Summary
        cost_summary = await pricing.calculate_cost(
            resource_type='llm', provider='gemini', 
            details={'action': 'ai_domain_summary'}
        )
        print(f"Cost for AI Domain Summary: {cost_summary} credits (Expected: 0.25)")
        assert cost_summary == 0.25
        
        # Test 2: Action-based cost for Stats Sync (2000 sites)
        cost_sync = await pricing.calculate_cost(
            resource_type='dataforseo', provider='dataforseo',
            details={'action': 'stats_sync', 'quantity': 2000}
        )
        print(f"Cost for Syncing 2000 sites: {cost_sync} credits (Expected: 0.16)")
        assert cost_sync == 0.16
        
        # Test 3: Action-based cost for Deep Content Analysis
        cost_deep = await pricing.calculate_cost(
            resource_type='llm', provider='openai',
            details={'action': 'deep_content_analysis'}
        )
        print(f"Cost for Deep Analysis: {cost_deep} credits (Expected: 1.0)")
        assert cost_deep == 1.0
        
        # Test 4: Default to Free Tier
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        user_sub = await pricing.get_user_subscription("test-user-id")
        print(f"User Tier: {user_sub['tier_id']} (Expected: free)")
        assert user_sub['tier_id'] == 'free'

    print("\n✅ Verification successful!")

if __name__ == "__main__":
    asyncio.run(verify_pricing_logic())
