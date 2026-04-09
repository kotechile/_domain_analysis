import os
import sys
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

sys.path.append(os.path.join(os.getcwd(), "backend", "src"))

from services.marketplace_batch_service import MarketplaceBatchService


class TestMarketplaceBatchService(unittest.IsolatedAsyncioTestCase):
    @patch("services.marketplace_batch_service.ProgressTracker.complete_job", new_callable=AsyncMock)
    @patch("services.marketplace_batch_service.ProgressTracker.update_progress", new_callable=AsyncMock)
    @patch("services.marketplace_batch_service.DataForSEOService")
    @patch("services.marketplace_batch_service.AuctionsService")
    @patch("services.marketplace_batch_service.CreditsService")
    @patch("services.marketplace_batch_service.get_database")
    @patch("services.pricing_service.PricingService")
    async def test_fill_metrics_enforces_has_statistics_false_and_respects_scored_filter(
        self,
        pricing_service_cls,
        get_database_mock,
        credits_service_cls,
        auctions_service_cls,
        dataforseo_service_cls,
        update_progress_mock,
        complete_job_mock,
    ):
        fake_db = Mock()
        get_database_mock.return_value = fake_db
        service = MarketplaceBatchService()
        service.get_refresh_costs = AsyncMock(
            return_value={"bulk_refresh_1k": 50, "force_refresh_1k": 150, "individual_deep_dive": 10}
        )
        service.auctions_service.get_auctions_missing_any_metric_with_filters = AsyncMock(
            return_value=[{"domain": "example.com"}]
        )
        service.credits_service.get_balance = AsyncMock(return_value={"balance": 1000})
        service.credits_service.deduct_credits = AsyncMock(return_value=True)
        service.n8n_service.trigger_marketplace_metrics_workflows = AsyncMock(
            return_value={"rank": {"status": "triggered"}, "backlinks": {"status": "triggered"}, "spam_score": {"status": "triggered"}}
        )
        service._fetch_and_store_traffic_metrics = AsyncMock(return_value=1)

        client = Mock()
        table_builder = Mock()
        table_builder.insert.return_value.execute = AsyncMock(return_value=Mock())
        client.table.return_value = table_builder
        fake_db._get_client = AsyncMock(return_value=client)

        pricing_instance = pricing_service_cls.return_value
        pricing_instance.calculate_action_cost = AsyncMock(return_value=1.25)

        await service.process_marketplace_refresh(
            user_id=uuid4(),
            filters={"scored": True, "preferred": True},
            force=False,
            job_id="job-123",
            sort_by="score",
            sort_order="desc",
        )

        service.auctions_service.get_auctions_missing_any_metric_with_filters.assert_awaited_once_with(
            filters={"scored": True, "preferred": True, "has_statistics": False},
            sort_by="score",
            sort_order="desc",
            limit=1000,
            force_refresh=False,
        )

    @patch("services.marketplace_batch_service.ProgressTracker.complete_job", new_callable=AsyncMock)
    @patch("services.marketplace_batch_service.ProgressTracker.update_progress", new_callable=AsyncMock)
    @patch("services.marketplace_batch_service.DataForSEOService")
    @patch("services.marketplace_batch_service.AuctionsService")
    @patch("services.marketplace_batch_service.CreditsService")
    @patch("services.marketplace_batch_service.get_database")
    @patch("services.pricing_service.PricingService")
    async def test_only_displayed_fill_metrics_preserves_display_order_and_only_fetches_unfilled_domains(
        self,
        pricing_service_cls,
        get_database_mock,
        credits_service_cls,
        auctions_service_cls,
        dataforseo_service_cls,
        update_progress_mock,
        complete_job_mock,
    ):
        fake_db = Mock()
        get_database_mock.return_value = fake_db
        service = MarketplaceBatchService()
        service.get_refresh_costs = AsyncMock(
            return_value={"bulk_refresh_1k": 50, "force_refresh_1k": 150, "individual_deep_dive": 10}
        )
        service.credits_service.get_balance = AsyncMock(return_value={"balance": 1000})
        service.credits_service.deduct_credits = AsyncMock(return_value=True)
        service.n8n_service.trigger_marketplace_metrics_workflows = AsyncMock(
            return_value={"rank": {"status": "triggered"}, "backlinks": {"status": "triggered"}, "spam_score": {"status": "triggered"}}
        )
        service._fetch_and_store_traffic_metrics = AsyncMock(return_value=2)

        fake_db.get_auctions_by_domains = AsyncMock(
            return_value=[
                {"domain": "third.com"},
                {"domain": "first.com"},
            ]
        )

        client = Mock()
        table_builder = Mock()
        table_builder.insert.return_value.execute = AsyncMock(return_value=Mock())
        client.table.return_value = table_builder
        fake_db._get_client = AsyncMock(return_value=client)

        pricing_instance = pricing_service_cls.return_value
        pricing_instance.calculate_action_cost = AsyncMock(return_value=1.25)

        await service.process_marketplace_refresh(
            user_id=uuid4(),
            filters={"scored": True},
            force=False,
            job_id="job-456",
            sort_by="expiration_date",
            sort_order="asc",
            prioritized_domains=[" first.com ", "second.com", "third.com", "first.com"],
            only_displayed=True,
        )

        fake_db.get_auctions_by_domains.assert_awaited_once_with(
            ["first.com", "second.com", "third.com"],
            filters={"scored": True, "has_statistics": False},
        )
        service.n8n_service.trigger_marketplace_metrics_workflows.assert_awaited_once_with(
            ["first.com", "third.com"],
            include_traffic=False,
        )

    @patch("services.marketplace_batch_service.ProgressTracker.complete_job", new_callable=AsyncMock)
    @patch("services.marketplace_batch_service.ProgressTracker.update_progress", new_callable=AsyncMock)
    @patch("services.marketplace_batch_service.DataForSEOService")
    @patch("services.marketplace_batch_service.AuctionsService")
    @patch("services.marketplace_batch_service.CreditsService")
    @patch("services.marketplace_batch_service.get_database")
    @patch("services.pricing_service.PricingService")
    async def test_process_refresh_marks_partial_failure_when_workflow_trigger_fails(
        self,
        pricing_service_cls,
        get_database_mock,
        credits_service_cls,
        auctions_service_cls,
        dataforseo_service_cls,
        update_progress_mock,
        complete_job_mock,
    ):
        fake_db = Mock()
        get_database_mock.return_value = fake_db
        service = MarketplaceBatchService()
        service.get_refresh_costs = AsyncMock(
            return_value={"bulk_refresh_1k": 50, "force_refresh_1k": 150, "individual_deep_dive": 10}
        )
        service.auctions_service.get_auctions_missing_any_metric_with_filters = AsyncMock(
            return_value=[{"domain": "example.com"}, {"domain": "example.net"}]
        )
        service.credits_service.get_balance = AsyncMock(return_value={"balance": 1000})
        service.credits_service.deduct_credits = AsyncMock(return_value=True)
        service.n8n_service.trigger_marketplace_metrics_workflows = AsyncMock(
            return_value={"rank": {"status": "triggered"}, "backlinks": {"status": "triggered"}, "spam_score": None}
        )
        service._fetch_and_store_traffic_metrics = AsyncMock(return_value=2)

        client = Mock()
        table_builder = Mock()
        table_builder.insert.return_value.execute = AsyncMock(return_value=Mock())
        client.table.return_value = table_builder
        fake_db._get_client = AsyncMock(return_value=client)

        pricing_instance = pricing_service_cls.return_value
        pricing_instance.calculate_action_cost = AsyncMock(return_value=1.25)

        await service.process_marketplace_refresh(
            user_id=uuid4(),
            filters={"scored": True},
            force=False,
            job_id="job-123",
            sort_by="expiration_date",
            sort_order="asc",
        )

        complete_job_mock.assert_awaited_once()
        args, kwargs = complete_job_mock.await_args
        self.assertEqual(args[0], "job-123")
        self.assertFalse(kwargs["success"])
        self.assertIn("Partial refresh", kwargs["message"])
        self.assertIn("Failed workflow triggers: spam_score", kwargs["message"])
        self.assertIn("Traffic updated immediately for 2", kwargs["message"])
        update_progress_mock.assert_awaited()
