import os
import sys
import unittest
from unittest.mock import AsyncMock, Mock

sys.path.append(os.path.join(os.getcwd(), "backend", "src"))

from services.auction_scoring_service import AuctionScoringService


class TestAuctionScoringService(unittest.IsolatedAsyncioTestCase):
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
        self.assertEqual(client.rpc.call_args_list[0].args[0], 'recalculate_auction_rankings_chunked')
        self.assertEqual(client.rpc.call_args_list[1].args[0], 'recalculate_auction_rankings')

    def test_missing_chunked_ranking_function_detection(self):
        error = Exception(
            "{'message': 'Could not find the function public.recalculate_auction_rankings_chunked(p_batch_size) in the schema cache', 'code': 'PGRST202'}"
        )
        self.assertTrue(AuctionScoringService._is_missing_chunked_ranking_function(error))

        unrelated_error = Exception("canceling statement due to statement timeout")
        self.assertFalse(AuctionScoringService._is_missing_chunked_ranking_function(unrelated_error))
