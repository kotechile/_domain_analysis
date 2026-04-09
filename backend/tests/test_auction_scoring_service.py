import os
import sys
import unittest
from unittest.mock import AsyncMock, Mock

sys.path.append(os.path.join(os.getcwd(), "backend", "src"))

from services.auction_scoring_service import AuctionScoringService


class TestAuctionScoringService(unittest.IsolatedAsyncioTestCase):
    async def test_recalculate_rankings_uses_stepwise_cursor_for_large_datasets(self):
        service = AuctionScoringService()
        service.get_processing_stats = AsyncMock(return_value={'scored_count': 1_608_816})
        service.recalculate_rankings_step = AsyncMock(side_effect=[
            {
                'success': True,
                'processed_count': 5000,
                'next_start_rank': 5001,
                'next_after_score': 88.1,
                'next_after_id': 'cursor-1',
                'total_scored': 1_608_816,
                'done': False,
            },
            {
                'success': True,
                'processed_count': 5000,
                'next_start_rank': 10001,
                'next_after_score': 87.7,
                'next_after_id': 'cursor-2',
                'total_scored': 1_608_816,
                'done': True,
            },
        ])
        service.db_service._get_client = AsyncMock(return_value=Mock())

        result = await service.recalculate_rankings(batch_size=5000, max_step_batches=10)

        self.assertTrue(result['success'])
        self.assertTrue(result['stepwise'])
        self.assertTrue(result['done'])
        self.assertEqual(result['processed_count'], 10000)
        self.assertEqual(result['next_after_id'], 'cursor-2')

    async def test_recalculate_rankings_falls_back_when_chunked_function_missing(self):
        service = AuctionScoringService()
        client = Mock()

        chunked_builder = Mock()
        chunked_builder.execute = AsyncMock(
            side_effect=Exception(
                "{'message': 'Could not find the function public.recalculate_auction_rankings_chunked(p_batch_size) in the schema cache', 'code': 'PGRST202'}"
            )
        )

        standard_builder = Mock()
        standard_builder.execute = AsyncMock(
            return_value=Mock(data={'success': True, 'ranked_count': 123})
        )

        client.rpc.side_effect = [chunked_builder, standard_builder]
        service.db_service._get_client = AsyncMock(return_value=client)
        service.get_processing_stats = AsyncMock(return_value={'scored_count': 1_608_816})

        result = await service.recalculate_rankings()

        self.assertEqual(result, {'success': True, 'ranked_count': 123})
        self.assertEqual(client.rpc.call_args_list[0].args[0], 'recalculate_auction_rankings_step')
        self.assertEqual(client.rpc.call_args_list[1].args[0], 'recalculate_auction_rankings_chunked')

    def test_missing_chunked_ranking_function_detection(self):
        error = Exception(
            "{'message': 'Could not find the function public.recalculate_auction_rankings_chunked(p_batch_size) in the schema cache', 'code': 'PGRST202'}"
        )
        self.assertTrue(AuctionScoringService._is_missing_chunked_ranking_function(error))

        unrelated_error = Exception("canceling statement due to statement timeout")
        self.assertFalse(AuctionScoringService._is_missing_chunked_ranking_function(unrelated_error))

    def test_missing_stepwise_ranking_function_detection(self):
        error = Exception(
            "{'message': 'Could not find the function public.recalculate_auction_rankings_step(p_batch_size,p_start_rank,p_after_score,p_after_id) in the schema cache', 'code': 'PGRST202'}"
        )
        self.assertTrue(AuctionScoringService._is_missing_stepwise_ranking_function(error))
