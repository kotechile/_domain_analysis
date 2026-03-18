
from typing import List, Dict, Any, Optional
import structlog
from datetime import datetime
from uuid import UUID

from services.database import get_database
from services.credits_service import CreditsService
from services.n8n_service import N8NService
from services.auctions_service import AuctionsService

logger = structlog.get_logger()

class MarketplaceBatchService:
    """Service for handling marketplace bulk and force refreshes with credits"""
    
    def __init__(self):
        self.db = get_database()
        self.credits_service = CreditsService(self.db)
        self.n8n_service = N8NService()
        self.auctions_service = AuctionsService()

    async def get_refresh_costs(self) -> Dict[str, int]:
        """Get calculated costs from global settings"""
        try:
            settings = await self.credits_service.get_global_settings()
            
            # Default fallback costs if settings not in DB
            bulk_cost = settings.get('bulk_refresh_1k_cost', {}).get('credits', 50)
            force_cost = settings.get('force_refresh_1k_cost', {}).get('credits', 150)
            deep_cost = settings.get('individual_deep_dive_cost', {}).get('credits', 10)
            
            return {
                "bulk_refresh_1k": int(bulk_cost),
                "force_refresh_1k": int(force_cost),
                "individual_deep_dive": int(deep_cost)
            }
        except Exception as e:
            logger.error("Failed to fetch fresh costs", error=str(e))
            return {"bulk_refresh_1k": 50, "force_refresh_1k": 150, "individual_deep_dive": 10}

    async def trigger_marketplace_refresh(
        self,
        user_id: UUID,
        filters: Dict[str, Any],
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Legacy synchronous method — now returns immediately with in_progress status.
        Use process_marketplace_refresh() for background processing.
        """
        return {
            "success": True,
            "in_progress": True,
            "message": "Refresh started — processing in background."
        }

    async def process_marketplace_refresh(
        self,
        user_id: UUID,
        filters: Dict[str, Any],
        force: bool = False
    ):
        """
        Background task: "Find and Fill" — trigger a DataForSEO refresh for up to 1,000 domains.
        This runs in the background and doesn't block the API response.

        force=True: Bypasses the missing-metrics and staleness checks (premium call).
        force=False: Fill-the-gaps behaviour — cheaper and idempotent.
        """
        try:
            costs = await self.get_refresh_costs()
            cost_key = "force_refresh_1k" if force else "bulk_refresh_1k"
            cost = costs[cost_key]

            description = f"{'Force' if force else 'Fill-the-Gaps'} marketplace refresh (up to 1,000 domains)"
            ref_id = f"refresh_{'force' if force else 'bulk'}_{int(datetime.utcnow().timestamp())}"

            logger.info(f"[Background] Starting {'force' if force else 'bulk'} refresh",
                       user_id=str(user_id), filters=filters, force=force)

            # 1. Find the domains BEFORE deducting credits
            logger.info(f"[Background] Finding domains with filters", filters=filters)
            domains_data = await self.auctions_service.get_auctions_missing_any_metric_with_filters(
                filters=filters,
                limit=1000,
                force_refresh=force
            )
            domain_names = [d['domain'] for d in domains_data]

            logger.info(f"[Background] Found {len(domain_names)} domains for refresh",
                       user_id=str(user_id), domain_count=len(domain_names), filters=filters)

            if not domain_names:
                logger.info(f"[Background] No domains needed refreshing - all domains have fresh metrics or match filters",
                           user_id=str(user_id), filters=filters)
                return

            # 2. Deduct credits only once we know there is work to do
            logger.info(f"[Background] Deducting {cost} credits", user_id=str(user_id))
            success = await self.credits_service.deduct_credits(
                user_id=user_id,
                amount=cost,
                description=description,
                reference_id=ref_id
            )

            if not success:
                logger.error(f"[Background] Insufficient credits", user_id=str(user_id), required=cost)
                return

            logger.info(f"[Background] Credits deducted successfully", user_id=str(user_id), cost=cost)

            # 3. Trigger DataForSEO via N8N (in smaller batches to avoid overwhelming N8N)
            import asyncio
            batch_size = 100
            total_batches = (len(domain_names) + batch_size - 1) // batch_size
            logger.info(f"[Background] Triggering N8N for {len(domain_names)} domains in {total_batches} batches",
                       user_id=str(user_id), domain_count=len(domain_names), batches=total_batches)

            for i in range(0, len(domain_names), batch_size):
                batch = domain_names[i:i + batch_size]
                try:
                    await self.n8n_service.trigger_bulk_page_summary_workflow(batch)
                    logger.info(f"[Background] Triggered N8N batch {i//batch_size + 1}/{total_batches}",
                               user_id=str(user_id), batch_size=len(batch), batch_num=i//batch_size + 1)
                    # Add delay between batches to prevent overwhelming the system
                    if i + batch_size < len(domain_names):
                        await asyncio.sleep(2)
                except Exception as n8n_err:
                    logger.error(f"[Background] Failed to trigger N8N batch {i//batch_size + 1}",
                                user_id=str(user_id), error=str(n8n_err))

            # 4. Record in refresh_history
            try:
                self.db.client.table('refresh_history').insert({
                    'user_id': str(user_id),
                    'batch_size': len(domain_names),
                    'credits_spent': cost,
                    'filters_used': filters
                }).execute()
                logger.info(f"[Background] Refresh history recorded", user_id=str(user_id))
            except Exception as hist_err:
                logger.warning("[Background] Failed to write refresh history", error=str(hist_err))

            logger.info(f"[Background] Refresh completed successfully",
                       user_id=str(user_id), domain_count=len(domain_names), cost=cost)

        except Exception as e:
            logger.error("[Background] Failed to process marketplace refresh",
                        user_id=str(user_id), error=str(e))
            import traceback
            logger.error("[Background] Exception traceback", traceback=traceback.format_exc())


    async def get_refresh_history(self, user_id: UUID, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the refresh history for a user"""
        response = self.db.client.table('refresh_history')\
            .select('*')\
            .eq('user_id', str(user_id))\
            .order('refreshed_at', desc=True)\
            .limit(limit)\
            .execute()
        return response.data

    async def refresh_single_domain(self, user_id: UUID, domain: str) -> Dict:
        """
        Refresh a single domain (Force Refresh)
        Cost: 5 credits (fixed or from settings)
        """
        # 1. Get cost
        costs = await self.get_refresh_costs()
        # Use individual_deep_dive cost or fallback to 5
        cost = costs.get("individual_deep_dive", 5)
        
        # 2. Deduct credits
        description = f"Force Refresh: {domain}"
        # Estimate dollar amount (simple ratio)
        dollar_amount = float(cost) * 0.001
        
        success = await self.credits_service.deduct_credits(
            user_id=user_id,
            amount=float(cost),
            description=description,
            dollar_amount=dollar_amount
        )
        
        if not success:
            return {"success": False, "error": "Insufficient credits"}
            
        # 3. Trigger N8N
        await self.n8n_service.trigger_bulk_page_summary_workflow([domain])
        
        # 4. Record History
        try:
            self.db.client.table('refresh_history').insert({
                'user_id': str(user_id),
                'batch_size': 1,
                'credits_spent': int(cost),
                'filters_used': {'domain': domain, 'type': 'single_refresh'}
            }).execute()
        except Exception as e:
            logger.error("Failed to record single refresh history", error=str(e))
            
        return {
            "success": True, 
            "message": f"Refresh triggered for {domain}",
            "credits_deducted": cost
        }
