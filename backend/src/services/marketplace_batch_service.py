
from typing import List, Dict, Any, Optional
import structlog
from datetime import datetime
from uuid import UUID

from services.database import get_database
from services.credits_service import CreditsService
from services.n8n_service import N8NService
from services.auctions_service import AuctionsService
from services.progress_tracker import ProgressTracker
from services.external_apis import DataForSEOService

logger = structlog.get_logger()

class MarketplaceBatchService:
    """Service for handling marketplace bulk and force refreshes with credits"""
    
    def __init__(self):
        self.db = get_database()
        self.credits_service = CreditsService(self.db)
        self.n8n_service = N8NService()
        self.auctions_service = AuctionsService()
        self.dataforseo_service = DataForSEOService()

    async def _fetch_and_store_traffic_metrics(self, domains: List[str], user_id: Optional[UUID] = None) -> int:
        """
        Fetch traffic metrics directly from DataForSEO Labs and store them in auctions.

        This path intentionally bypasses n8n. It uses the bulk traffic estimation
        live endpoint for up to 1000 domains and persists organic traffic plus
        keyword count from metrics.organic.
        """
        if not domains:
            return 0

        items = await self.dataforseo_service.fetch_bulk_traffic_estimation_live(domains, user_id=user_id)
        if not items:
            logger.warning("No direct traffic metrics returned from DataForSEO", domain_count=len(domains))
            return 0

        updated = 0
        for item in items:
            target = item.get('target')
            metrics = item.get('metrics', {})
            organic = metrics.get('organic', {}) if isinstance(metrics, dict) else {}

            if not target:
                continue

            traffic_data = {
                "organic_traffic": organic.get('etv', 0) or 0,
                "etv": organic.get('etv', 0) or 0,
                "organic_keywords": organic.get('count', 0) or 0,
                "keywords_count": organic.get('count', 0) or 0,
                "traffic_timestamp": datetime.utcnow().isoformat(),
            }

            success = await self.db.update_auction_traffic_data(target, traffic_data)
            if success:
                updated += 1

        logger.info("Stored direct traffic metrics from backend", requested=len(domains), updated=updated)
        return updated

    async def get_refresh_costs(self) -> Dict[str, int]:
        """Get calculated costs from global settings"""
        try:
            settings = await self.credits_service.get_global_settings()
            
            # Default fallback costs if settings not in DB
            bulk_cost = settings.get('bulk_refresh_1k_cost', {}).get('credits', 50)
            force_cost = settings.get('force_refresh_1k_cost', {}).get('credits', 150)
            deep_cost = settings.get('individual_deep_dive_cost', {}).get('credits', 10)
            
            return { "bulk_refresh_1k": int(bulk_cost), "force_refresh_1k": int(force_cost), "individual_deep_dive": int(deep_cost) }
        except Exception as e:
            logger.error("Failed to fetch fresh costs", error=str(e))
            return {"bulk_refresh_1k": 50, "force_refresh_1k": 150, "individual_deep_dive": 10}

    async def trigger_marketplace_refresh( self, user_id: UUID, filters: Dict[str, Any], force: bool = False ) -> Dict[str, Any]:
        """
        Legacy synchronous method — now returns immediately with in_progress status. Use process_marketplace_refresh() for background processing. """
        return { "success": True, "in_progress": True, "message": "Refresh started — processing in background." }

    async def process_marketplace_refresh( self, user_id: Any, filters: Dict[str, Any], force: bool = False, job_id: Optional[str] = None, sort_by: str = 'expiration_date', sort_order: str = 'asc', prioritized_domains: Optional[List[str]] = None, only_displayed: bool = False ):
        """
        Background task: "Find and Fill" — trigger a DataForSEO refresh for up to 1,000 domains.
        This runs in the background and doesn't block the API response.

        force=True: Bypasses the missing-metrics and staleness checks (premium call).
        force=False: Fill-the-gaps behaviour — cheaper and idempotent.
        prioritized_domains: Optional list of domains to prioritize in the refresh.
        """
        # File-based debug logging to help identify why tasks stop
        DEBUG_LOG = '/tmp/refresh_background.log'

        try:
            with open(DEBUG_LOG, 'a') as f:
                f.write(f"\n--- REFRESH START: {datetime.utcnow().isoformat()} ---\n")
                f.write(f"Job: {job_id}, User: {user_id}\n")
                f.write(f"Filters: {filters}\n")
                f.write(f"Sort: {sort_by} {sort_order}\n")
                f.write(f"Prioritized domains: {len(prioritized_domains) if prioritized_domains else 0}\n")

            # 1. Costs and setup
            costs = await self.get_refresh_costs()
            cost_key = "force_refresh_1k" if force else "bulk_refresh_1k"
            cost = int(costs[cost_key])

            description = f"{'Force' if force else 'Fill-the-Gaps'} marketplace refresh (up to 1,000 domains)"
            ref_id = f"refresh_{'force' if force else 'bulk'}_{int(datetime.utcnow().timestamp())}"

            logger.info(f"[Background] Starting {'force' if force else 'bulk'} refresh", user_id=str(user_id), filters=filters, force=force, job_id=job_id, prioritized_count=len(prioritized_domains) if prioritized_domains else 0, only_displayed=only_displayed)

            # 2. Find the domains
            # Fill Metrics should only target domains that have not been populated yet.
            refresh_filters = dict(filters or {})
            if not force:
                refresh_filters['has_statistics'] = False

            # If only_displayed mode, we'll just use the prioritized domains directly
            domain_names = []

            if only_displayed and prioritized_domains:
                # In "only displayed" mode, refresh only the rows the user is looking at,
                # while still respecting the same fill-metrics rules as the bulk selector.
                prioritized_order = []
                seen_domains = set()
                for domain in prioritized_domains:
                    cleaned = domain.strip().lower() if domain else ''
                    if cleaned and cleaned not in seen_domains:
                        prioritized_order.append(cleaned)
                        seen_domains.add(cleaned)

                domains_data = await self.db.get_auctions_by_domains(prioritized_order, filters=refresh_filters)
                domains_by_name = {
                    record['domain'].lower(): record['domain']
                    for record in domains_data
                    if record.get('domain')
                }
                domain_names = [domains_by_name[name] for name in prioritized_order if name in domains_by_name]
                logger.info(
                    "[Background] Only displayed mode - using displayed domains that still need metrics",
                    domain_count=len(domain_names),
                )
            else:
                # Standard mode: find up to 1000 domains matching filters
                logger.info(f"[Background] Finding domains with filters", filters=refresh_filters)
                domains_data = await self.auctions_service.get_auctions_missing_any_metric_with_filters(
                    filters=refresh_filters, sort_by=sort_by, sort_order=sort_order, limit=1000, force_refresh=force
                )
                domain_names = [d['domain'] for d in domains_data]

            # 3. Handle prioritized domains (reordering for standard mode)
            # In only_displayed mode, we already filtered to just those domains
            if prioritized_domains and not only_displayed:
                # Normalize prioritized domains (remove duplicates, strip whitespace)
                prioritized_set = set(d.strip().lower() for d in prioritized_domains if d and d.strip())

                # Check which prioritized domains are already in the filtered/sorted candidate list
                prioritized_in_db = [d for d in domain_names if d.lower() in prioritized_set]
                prioritized_missing = [d for d in prioritized_set if d not in [x.lower() for x in domain_names]]

                if prioritized_missing:
                    logger.info(f"[Background] Some prioritized domains not in current filter results, fetching them separately",
                        missing_count=len(prioritized_missing))
                    # Fetch the missing prioritized domains directly from DB
                    missing_domains = await self.db.get_auctions_by_domains(list(prioritized_missing), filters=refresh_filters)
                    # Add them to the domain_names list
                    prioritized_in_db.extend([d['domain'] for d in missing_domains])

                prioritized_available = {d.lower() for d in prioritized_in_db}

                # Create final list: prioritized first (in their original order), then remaining domains
                final_domains = []
                seen = set()

                # Add prioritized domains first (maintaining original order)
                for d in prioritized_domains:
                    d_clean = d.strip()
                    if d_clean and d_clean.lower() not in seen and d_clean.lower() in prioritized_available:
                        final_domains.append(d_clean)
                        seen.add(d_clean.lower())

                # Add remaining domains from the filtered results (up to 1000 total)
                for d in domain_names:
                    if d.lower() not in seen and len(final_domains) < 1000:
                        final_domains.append(d)
                        seen.add(d.lower())

                domain_names = final_domains
                logger.info(f"[Background] Prioritized domains reordered", total_domains=len(domain_names), prioritized_included=len([d for d in prioritized_domains if d.strip().lower() in seen]))

            with open(DEBUG_LOG, 'a') as f:
                f.write(f"Found {len(domain_names)} domains\n")

            if not domain_names:
                logger.info(f"[Background] No domains needed refreshing", user_id=str(user_id), filters=filters)
                if job_id:
                    await ProgressTracker.complete_job( job_id, success=True, message="No domains need refreshing - all have fresh metrics" )
                with open(DEBUG_LOG, 'a') as f:
                    f.write("No candidates found - EXITING\n")
                return

            # 4. Costs and credit deduction
            from services.pricing_service import PricingService
            pricing_service = PricingService()
            
            # Calculate dynamic cost based on ACTUAL domains found
            # 'stats_sync' action is used for tiered domain metrics
            # If force=True, we use 'force_refresh_1k' as a base but still scale it
            cost = await pricing_service.calculate_action_cost('stats_sync', len(domain_names))
            
            # If force=True, we might want to charge more or use a different action
            if force:
                # Force refresh is 3x more expensive than gap filling
                cost = cost * 3.0
            
            # Round cost to 2 decimal places for credits
            cost = round(max(0.01, float(cost)), 2)

            # Robust user_id conversion
            from uuid import UUID
            user_id_obj = user_id
            if isinstance(user_id, str):
                try: 
                    user_id_obj = UUID(user_id)
                except:
                    with open(DEBUG_LOG, 'a') as f:
                        f.write(f"Could not convert {user_id} to UUID, using as is\n")

            # Ensure user has a credit record (this also handles new users)
            try:
                await self.credits_service.get_balance(user_id_obj)
            except Exception as cr_err:
                logger.warning("Failed to check/init credit balance", user_id=str(user_id), error=str(cr_err))

            success = await self.credits_service.deduct_credits( 
                user_id=user_id_obj, 
                amount=cost, 
                description=description, 
                reference_id=ref_id,
                dollar_amount=cost * 0.001 # Estimate 
            )

            if not success:
                logger.error(f"[Background] Insufficient credits", user_id=str(user_id), required=cost)
                if job_id:
                    await ProgressTracker.complete_job( job_id, success=False, message=f"Insufficient credits. Requires {cost} credits." )
                with open(DEBUG_LOG, 'a') as f:
                    f.write(f"Insufficient credits (Required {cost}) - EXITING\n")
                return

            logger.info(f"[Background] Credits deducted successfully", user_id=str(user_id), cost=cost)


            # 4. Trigger N8N
            import asyncio
            batch_size = 1000  # Increased from 20 to 1000 for efficiency
            total_batches = (len(domain_names) + batch_size - 1) // batch_size
            
            if job_id:
                await ProgressTracker.update_progress( job_id, processed_items=0, total_batches=total_batches, current_batch=0, message=f"Triggering N8N for {len(domain_names)} domains..." )

            processed_count = 0
            failed_count = 0
            traffic_updated_total = 0
            successful_workflows = set()
            failed_workflows = set()

            for i in range(0, len(domain_names), batch_size):
                batch_num = i // batch_size + 1
                batch = domain_names[i:i + batch_size]
                try:
                    logger.info(f"[Background] Triggering direct marketplace metrics via n8n for batch {batch_num}", domain_count=len(batch))
                    workflow_results = await self.n8n_service.trigger_marketplace_metrics_workflows(batch, include_traffic=False)
                    batch_successful_workflows = [name for name, value in workflow_results.items() if value]
                    batch_failed_workflows = [name for name, value in workflow_results.items() if not value]

                    successful_workflows.update(batch_successful_workflows)
                    failed_workflows.update(batch_failed_workflows)

                    processed_count += len(batch)

                    if job_id:
                        progress_message = (
                            f"Queued {processed_count}/{len(domain_names)} domains for provider refresh. "
                            f"Traffic updated for {traffic_updated_total} so far. "
                            f"Successful triggers: {', '.join(sorted(successful_workflows)) or 'none'}."
                        )
                        if failed_workflows:
                            progress_message += f" Trigger failures: {', '.join(sorted(failed_workflows))}."

                        await ProgressTracker.update_progress(
                            job_id,
                            processed_items=processed_count,
                            failed_items=failed_count,
                            current_batch=batch_num,
                            total_batches=total_batches,
                            message=progress_message,
                        )

                    traffic_updated = 0
                    try:
                        logger.info(f"[Background] Fetching direct backend traffic metrics for batch {batch_num}", domain_count=len(batch))
                        traffic_updated = await asyncio.wait_for(
                            self._fetch_and_store_traffic_metrics(batch, user_id=user_id if isinstance(user_id, UUID) else None),
                            timeout=45,
                        )
                        traffic_updated_total += traffic_updated
                    except asyncio.TimeoutError:
                        failed_workflows.add("traffic")
                        logger.warning(
                            "[Background] Direct traffic fetch timed out; continuing without blocking refresh completion",
                            batch_num=batch_num,
                            domain_count=len(batch),
                        )
                    except Exception as traffic_err:
                        failed_workflows.add("traffic")
                        logger.error(
                            "[Background] Failed to fetch direct backend traffic metrics",
                            batch_num=batch_num,
                            domain_count=len(batch),
                            error=str(traffic_err),
                        )

                    if job_id:
                        progress_message = (
                            f"Queued {processed_count}/{len(domain_names)} domains for provider refresh. "
                            f"Traffic updated for {traffic_updated_total} so far. "
                            f"Successful triggers: {', '.join(sorted(successful_workflows)) or 'none'}."
                        )
                        if failed_workflows:
                            progress_message += f" Trigger failures: {', '.join(sorted(failed_workflows))}."

                        await ProgressTracker.update_progress(
                            job_id,
                            processed_items=processed_count,
                            failed_items=failed_count,
                            current_batch=batch_num,
                            total_batches=total_batches,
                            message=progress_message,
                        )

                    if i + batch_size < len(domain_names):
                        await asyncio.sleep(2)
                except Exception as n8n_err:
                    failed_count += len(batch)
                    logger.error(f"[Background] Failed to trigger N8N batch {batch_num}", error=str(n8n_err))
                    with open(DEBUG_LOG, 'a') as f:
                        f.write(f"N8N Error (Batch {batch_num}): {str(n8n_err)}\n")

            # 5. Record history
            try:
                await (await self.db._get_client()).table('refresh_history').insert({ 'user_id': str(user_id), 'batch_size': len(domain_names), 'credits_spent': cost, 'filters_used': filters }).execute()
            except Exception as h_err:
                logger.warning("Failed to record history", error=str(h_err))

            # 6. Complete job
            if job_id:
                failed_workflow_list = sorted(failed_workflows)
                successful_workflow_list = sorted(successful_workflows)

                if failed_workflow_list:
                    completion_message = (
                        f"Partial refresh for {processed_count} domains. "
                        f"Traffic updated immediately for {traffic_updated_total}. "
                        f"Successful workflow triggers: {', '.join(successful_workflow_list) or 'none'}. "
                        f"Failed workflow triggers: {', '.join(failed_workflow_list)}."
                    )
                    await ProgressTracker.complete_job(job_id, success=False, message=completion_message)
                else:
                    completion_message = (
                        f"Queued refresh for {processed_count} domains. "
                        f"Traffic updated immediately for {traffic_updated_total}. "
                        f"Rank/backlinks/spam results continue syncing asynchronously."
                    )
                    await ProgressTracker.complete_job(job_id, success=True, message=completion_message)
            
            with open(DEBUG_LOG, 'a') as f:
                f.write(f"--- REFRESH COMPLETE: {datetime.utcnow().isoformat()} ---\n")

        except Exception as e:
            logger.error("[Background] Failed to process marketplace refresh", user_id=str(user_id), error=str(e), job_id=job_id)
            with open(DEBUG_LOG, 'a') as f:
                f.write(f"CRITICAL ERROR: {str(e)}\n")
                import traceback
                f.write(traceback.format_exc())
            if job_id:
                await ProgressTracker.complete_job( job_id, success=False, message=f"Failed: {str(e)[:100]}" )



    async def get_refresh_history(self, user_id: UUID, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the refresh history for a user"""
        response = await (await self.db._get_client()).table('refresh_history').select('*').eq('user_id', str(user_id)).order('refreshed_at', desc=True).limit(limit).execute()
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
        # ) Estimate dollar amount (simple ratio
        dollar_amount = float(cost) * 0.001
        
        success = await self.credits_service.deduct_credits( user_id=user_id, amount=float(cost), description=description, dollar_amount=dollar_amount )
        
        if not success:
            return {"success": False, "error": "Insufficient credits"}
            
        # 3. Trigger N8N
        await self.n8n_service.trigger_marketplace_metrics_workflows([domain], include_traffic=False)
        await self._fetch_and_store_traffic_metrics([domain], user_id=user_id)
        
        # 4. Record History
        try:
            await (await self.db._get_client()).table('refresh_history').insert({ 'user_id': str(user_id), 'batch_size': 1, 'credits_spent': int(cost), 'filters_used': {'domain': domain, 'type': 'single_refresh'} }).execute()
        except Exception as e:
            logger.error("Failed to record single refresh history", error=str(e))
            
        return { "success": True, "message": f"Refresh triggered for {domain}", "credits_deducted": cost }
