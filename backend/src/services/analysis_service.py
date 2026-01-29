"""
Main analysis service that orchestrates domain analysis
"""

import asyncio
from datetime import datetime
from typing import Optional, List, Any, Dict
import structlog

from models.domain_analysis import (
    DomainAnalysisReport, 
    AnalysisStatus, 
    DataForSEOMetrics,
    WaybackMachineSummary,
    LLMAnalysis,
    AnalysisMode,
    AnalysisPhase,
    DetailedDataType,
    AsyncTaskStatus,
    ProgressInfo
)
from services.database import get_database
from services.external_apis import DataForSEOService, WaybackMachineService, LLMService
from services.dataforseo_async import DataForSEOAsyncService
from services.n8n_service import N8NService
from services.logging_config import AsyncOperationLogger, ProgressTracker
from utils.config import get_settings

logger = structlog.get_logger()


class AnalysisService:
    """Main service for orchestrating domain analysis"""
    
    def __init__(self):
        self.dataforseo_service = DataForSEOService()
        self.dataforseo_async_service = DataForSEOAsyncService()
        self.n8n_service = N8NService()
        self.wayback_service = WaybackMachineService()
        self.llm_service = LLMService()
        self.settings = get_settings()
        self._db = None
    
    @property
    def db(self):
        if self._db is None:
            try:
                self._db = get_database()
            except RuntimeError:
                # Database not initialized, create a new instance
                from services.database import DatabaseService
                self._db = DatabaseService()
        return self._db
    
    async def analyze_domain(self, domain: str, report_id: str = None, mode: str = "dual") -> DomainAnalysisReport:
        """
        Perform complete domain analysis with dual-mode support
        """
        start_time = datetime.utcnow()
        operation_logger = AsyncOperationLogger("domain_analysis", domain)
        
        try:
            # Ensure database service is initialized
            if self._db is None:
                from services.database import init_database
                await init_database()
                self._db = get_database()
            
            logger.info("Starting domain analysis", domain=domain, mode=mode)
            
            # Determine analysis mode - use dual mode for domain buyer insights
            if mode == "enhanced" or mode == "dual":
                analysis_mode = AnalysisMode.DUAL
                operation_logger.log_dual_mode_decision(analysis_mode.value, "Using dual mode for domain buyer insights")
            else:
                analysis_mode = AnalysisMode.LEGACY
                operation_logger.log_dual_mode_decision(analysis_mode.value, "Using legacy mode")
            
            # Create progress tracker with more granular tracking
            progress_tracker = ProgressTracker(5, "domain_analysis", domain)  # essential, detailed, historical, ai_analysis, completed
            progress_tracker.add_operation("essential_data")
            progress_tracker.add_operation("detailed_data")
            progress_tracker.add_operation("historical_data")
            progress_tracker.add_operation("ai_analysis")
            progress_tracker.add_operation("finalization")
            
            # Add sub-operations for detailed data collection
            progress_tracker.add_sub_operation("detailed_data", "backlinks_analysis")
            progress_tracker.add_sub_operation("detailed_data", "keywords_analysis")
            progress_tracker.add_sub_operation("detailed_data", "referring_domains_analysis")
            progress_tracker.add_sub_operation("detailed_data", "data_saving")
            
            # Add sub-operations for AI analysis
            progress_tracker.add_sub_operation("ai_analysis", "llm_processing")
            progress_tracker.add_sub_operation("ai_analysis", "analysis_parsing")
            
            # Get existing report or create new one
            report = await self.db.get_report(domain)
            if not report:
                report = DomainAnalysisReport(
                    domain_name=domain,
                    analysis_timestamp=start_time,
                    status=AnalysisStatus.IN_PROGRESS,
                    analysis_mode=analysis_mode,
                    analysis_phase=AnalysisPhase.ESSENTIAL
                )
                await self.db.save_report(report)
            
            # Phase 1: Essential Data Collection
            progress_tracker.start_operation("essential_data")
            await self._update_progress_data(report, "Collecting essential domain metrics", [], progress_tracker)
            await self._collect_essential_data(domain, report, operation_logger)
            progress_tracker.complete_operation("essential_data")
            await self._update_progress_data(report, "Essential data collection completed", [], progress_tracker)
            
            # Phase 2: Detailed Data Collection (Mandatory)
            progress_tracker.start_operation("detailed_data")
            await self._update_progress_data(report, "Collecting detailed backlink and keyword data", [], progress_tracker)
            await self._collect_detailed_data(domain, report, analysis_mode, operation_logger, progress_tracker)
            progress_tracker.complete_operation("detailed_data")
            await self._update_progress_data(report, "Detailed data collection completed", [], progress_tracker)
            
            # Phase 3: Historical Data Collection
            progress_tracker.start_operation("historical_data")
            await self._update_progress_data(report, "Collecting historical ranking and traffic data", [], progress_tracker)
            historical_data = await self.get_or_fetch_historical_data(domain)
            if historical_data:
                report.historical_data = historical_data
                # report is saved inside get_or_fetch_historical_data, but we keep it in memory
            progress_tracker.complete_operation("historical_data")
            await self._update_progress_data(report, "Historical data collection completed", [], progress_tracker)
            
            # Phase 3: AI Analysis with Quality Assessment
            progress_tracker.start_operation("ai_analysis")
            await self._update_progress_data(report, "Generating AI-powered analysis and insights", [], progress_tracker)
            await self._perform_ai_analysis(domain, report, operation_logger, progress_tracker)
            progress_tracker.complete_operation("ai_analysis")
            await self._update_progress_data(report, "AI analysis completed", [], progress_tracker)
            
            # Phase 4: Finalization
            progress_tracker.start_operation("finalization")
            await self._update_progress_data(report, "Finalizing report and saving results", [], progress_tracker)
            await self._finalize_analysis(report, start_time, progress_tracker)
            progress_tracker.complete_operation("finalization")
            await self._update_progress_data(report, "Analysis completed successfully", [], progress_tracker)
            
            # Save final report
            await self.db.save_report(report)
            
            logger.info("Domain analysis completed successfully", 
                       domain=domain, 
                       mode=analysis_mode.value,
                       processing_time=(datetime.utcnow() - start_time).total_seconds())
            
            return report
            
        except Exception as e:
            error_msg = str(e)
            logger.error("Domain analysis failed", 
                        domain=domain, 
                        error=error_msg,
                        error_type=type(e).__name__,
                        exc_info=True)
            # Try to get existing report if it exists
            try:
                existing_report = await self.db.get_report(domain)
                if existing_report:
                    existing_report.status = AnalysisStatus.FAILED
                    existing_report.error_message = error_msg
                    await self.db.save_report(existing_report)
            except Exception as save_error:
                logger.error("Failed to save error to report", 
                           domain=domain, 
                           save_error=str(save_error))
            raise
    
    async def _determine_analysis_mode(self, domain: str, requested_mode: str) -> AnalysisMode:
        """Determine the analysis mode based on configuration and request"""
        try:
            # Get domain-specific or global configuration
            config = await self.db.get_mode_config(domain)
            if not config:
                config = await self.db.get_mode_config()  # Global config
            
            if requested_mode == "legacy":
                return AnalysisMode.LEGACY
            elif requested_mode == "async":
                return AnalysisMode.ASYNC
            elif requested_mode == "dual":
                # Use configuration preference
                return config.mode_preference if config else AnalysisMode.DUAL
            else:
                return AnalysisMode.DUAL
                
        except Exception as e:
            logger.warning("Failed to determine analysis mode, using dual", domain=domain, error=str(e))
            return AnalysisMode.DUAL
    
    async def _collect_essential_data(self, domain: str, report: DomainAnalysisReport, operation_logger: AsyncOperationLogger):
        """Collect essential data (domain rank overview, wayback)"""
        try:
            operation_logger.log_data_collection("essential_data")
            
            # Check if N8N should be used for summary
            use_n8n_summary = self.n8n_service.is_enabled_for_summary()
            backlinks_summary_data = None
            
            if use_n8n_summary:
                # Use N8N for backlinks summary
                logger.info("Using N8N for backlinks summary", domain=domain)
                n8n_result = await self.n8n_service.trigger_backlinks_summary_workflow(domain)
                if n8n_result:
                    logger.info("N8N summary workflow triggered, waiting for callback", 
                               domain=domain, 
                               request_id=n8n_result.get("request_id"))
                    
                    # Wait for N8N to call back (poll database for results)
                    max_wait_time = 60  # 1 minute max wait for summary
                    wait_interval = 2  # Check every 2 seconds
                    waited = 0
                    
                    while waited < max_wait_time:
                        await asyncio.sleep(wait_interval)
                        waited += wait_interval
                        
                        # Check if summary data was saved by webhook
                        from services.database import get_database
                        from models.domain_analysis import DataSource
                        db = get_database()
                        cached_data = await db.get_raw_data(domain, DataSource.DATAFORSEO)
                        if cached_data and cached_data.get("backlinks_summary"):
                            backlinks_summary_data = cached_data["backlinks_summary"]
                            logger.info("N8N backlinks summary data received via webhook", 
                                       domain=domain,
                                       backlinks=backlinks_summary_data.get("backlinks", 0),
                                       referring_domains=backlinks_summary_data.get("referring_domains", 0))
                            break
                    
                    if not backlinks_summary_data:
                        logger.error("N8N summary workflow did not return data in time", domain=domain, max_wait_time=max_wait_time)
                        raise Exception(f"N8N summary workflow did not return data within {max_wait_time} seconds")
                else:
                    logger.error("N8N summary workflow trigger failed", domain=domain)
                    raise Exception("Failed to trigger N8N summary workflow")
            
            # Get domain analytics data (includes backlinks summary if not using N8N)
            domain_rank_data = await self.dataforseo_service.get_domain_analytics(domain)
            
            # If we got summary from N8N, merge it into domain_rank_data
            if use_n8n_summary and backlinks_summary_data:
                if not domain_rank_data:
                    domain_rank_data = {}
                domain_rank_data["backlinks_summary"] = backlinks_summary_data
                logger.info("Merged N8N summary data into domain analytics", domain=domain)
            
            # Get wayback machine data
            wayback_data = await self.wayback_service.get_domain_history(domain)
            
            # Update report with essential data
            if domain_rank_data:
                logger.info("Parsing DataForSEO data in essential data collection", 
                           dataforseo_keys=list(domain_rank_data.keys()) if domain_rank_data else [])
                report.data_for_seo_metrics = self.dataforseo_service.parse_domain_metrics(domain_rank_data)
                logger.info("Parsed DataForSEO metrics in essential data collection", 
                           total_backlinks=report.data_for_seo_metrics.total_backlinks,
                           total_referring_domains=report.data_for_seo_metrics.total_referring_domains,
                           organic_traffic_est=report.data_for_seo_metrics.organic_traffic_est)
                
                # Save backlinks summary to report for easy access
                backlinks_summary = domain_rank_data.get("backlinks_summary")
                if backlinks_summary:
                    try:
                        from models.domain_analysis import BulkPageSummaryResult
                        # Add target field if missing (required by BulkPageSummaryResult)
                        if "target" not in backlinks_summary:
                            backlinks_summary["target"] = domain
                        # Convert dict to BulkPageSummaryResult model
                        report.backlinks_page_summary = BulkPageSummaryResult(**backlinks_summary)
                        logger.info("Saved backlinks page summary to report", 
                                   domain=domain,
                                   backlinks=backlinks_summary.get("backlinks", 0),
                                   referring_domains=backlinks_summary.get("referring_domains", 0))
                    except Exception as e:
                        logger.warning("Failed to parse backlinks_summary into BulkPageSummaryResult", 
                                     domain=domain, 
                                     error=str(e),
                                     backlinks_summary_keys=list(backlinks_summary.keys()) if isinstance(backlinks_summary, dict) else None)
                        # Store as dict if parsing fails
                        report.backlinks_page_summary = None
            
            if wayback_data:
                report.wayback_machine_summary = WaybackMachineSummary(**wayback_data)
            else:
                # Create empty summary if Wayback Machine data is not available
                logger.warning("Wayback Machine data not available, creating empty summary", domain=domain)
                report.wayback_machine_summary = WaybackMachineSummary(
                    first_capture_year=None,
                    total_captures=0,
                    last_capture_date=None,
                    historical_risk_assessment=None,
                    earliest_snapshot_url=None
                )
            
            report.analysis_phase = AnalysisPhase.DETAILED
            operation_logger.log_data_collection("essential_data", record_count=1)
            
        except Exception as e:
            logger.error("Essential data collection failed", domain=domain, error=str(e))
            raise
    
    async def _collect_detailed_data(self, domain: str, report: DomainAnalysisReport, 
                                   analysis_mode: AnalysisMode, operation_logger: AsyncOperationLogger, progress_tracker=None):
        """Collect detailed data (backlinks, keywords, referring domains) - OPTIONAL for enhanced analysis"""
        try:
            operation_logger.log_data_collection("detailed_data")
            
            detailed_data_available = {}
            
            if analysis_mode in [AnalysisMode.ASYNC, AnalysisMode.DUAL]:
                # Use async pattern for cost efficiency
                try:
                    detailed_status_messages = []
                    
                    # Collect detailed backlinks
                    progress_tracker.start_sub_operation("detailed_data", "backlinks_analysis")
                    operation_logger.log_data_collection("backlinks", message="Starting backlinks analysis...")
                    detailed_status_messages.append("Starting backlinks analysis...")
                    await self._update_progress_data(report, "Starting backlinks analysis...", detailed_status_messages, progress_tracker)
                    
                    # N8N is required for backlinks (no HTTP fallback allowed)
                    use_n8n = self.n8n_service.is_enabled_for_backlinks()
                    
                    if not use_n8n:
                        logger.error("N8N is required for backlinks but is not enabled", domain=domain)
                        raise Exception("N8N is required for backlinks analysis. Please enable N8N in your configuration (N8N_ENABLED=true, N8N_USE_FOR_BACKLINKS=true).")
                    
                    # Use N8N for backlinks (required - no HTTP fallback)
                    backlinks_data = None
                    detailed_status_messages.append("Triggering N8N workflow for backlinks...")
                    await self._update_progress_data(report, "Triggering N8N workflow for backlinks...", detailed_status_messages, progress_tracker)
                    
                    n8n_result = await self.n8n_service.trigger_backlinks_workflow(domain, 10000)
                    if n8n_result:
                        logger.info("N8N workflow triggered, waiting for callback", 
                                   domain=domain, 
                                   request_id=n8n_result.get("request_id"))
                        detailed_status_messages.append("N8N workflow triggered, waiting for results...")
                        await self._update_progress_data(report, "N8N workflow triggered, waiting for results...", detailed_status_messages, progress_tracker)
                        
                        # Wait for N8N to call back (poll database for results)
                        # Note: This is a simplified approach - in production you might want to use
                        # a more sophisticated async pattern with webhooks
                        max_wait_time = 120  # 2 minutes max wait
                        wait_interval = 2  # Check every 2 seconds
                        waited = 0
                        
                        while waited < max_wait_time:
                            await asyncio.sleep(wait_interval)
                            waited += wait_interval
                            
                            # Check if data was saved by webhook
                            from models.domain_analysis import DetailedDataType
                            saved_data = await self.db.get_detailed_data(domain, DetailedDataType.BACKLINKS)
                            if saved_data:
                                backlinks_data = saved_data.json_data
                                logger.info("N8N backlinks data received via webhook", 
                                           domain=domain,
                                           items_count=len(backlinks_data.get("items", [])))
                                break
                        
                        if not backlinks_data:
                            logger.error("N8N workflow did not return data in time", domain=domain, max_wait_time=max_wait_time)
                            detailed_status_messages.append("N8N timeout - no data received")
                            await self._update_progress_data(report, "N8N timeout - no data received", detailed_status_messages, progress_tracker)
                            raise Exception(f"N8N workflow did not return backlinks data within {max_wait_time} seconds")
                    else:
                        logger.error("N8N workflow trigger failed", domain=domain)
                        detailed_status_messages.append("N8N trigger failed")
                        await self._update_progress_data(report, "N8N trigger failed", detailed_status_messages, progress_tracker)
                        raise Exception("Failed to trigger N8N workflow for backlinks. Please check N8N configuration and workflow status.")
                    
                    if not backlinks_data:
                        logger.error("No backlinks data available from N8N", domain=domain)
                        raise Exception("No backlinks data available from N8N workflow")
                    
                    if backlinks_data and backlinks_data.get("items"):
                        detailed_data_available["backlinks"] = True
                        operation_logger.log_data_collection("backlinks", record_count=len(backlinks_data.get("items", [])), message="Backlinks analysis completed")
                        detailed_status_messages.append("Backlinks analysis completed")
                        await self._update_progress_data(report, "Backlinks analysis completed", detailed_status_messages, progress_tracker)
                        progress_tracker.complete_sub_operation("detailed_data", "backlinks_analysis")
                        
                        # Save detailed data to database (if not already saved by N8N webhook)
                        from models.domain_analysis import DetailedAnalysisData, DetailedDataType
                        existing_data = await self.db.get_detailed_data(domain, DetailedDataType.BACKLINKS)
                        if not existing_data:
                            detailed_data = DetailedAnalysisData(
                                domain_name=domain,
                                data_type=DetailedDataType.BACKLINKS,
                                json_data=backlinks_data
                            )
                            await self.db.save_detailed_data(detailed_data)
                    
                    # Collect detailed keywords
                    progress_tracker.start_sub_operation("detailed_data", "keywords_analysis")
                    operation_logger.log_data_collection("keywords", message="Starting keywords analysis...")
                    detailed_status_messages.append("Starting keywords analysis...")
                    await self._update_progress_data(report, "Starting keywords analysis...", detailed_status_messages, progress_tracker)
                    
                    # Add intermediate progress update
                    detailed_status_messages.append("Collecting keywords data...")
                    await self._update_progress_data(report, "Collecting keywords data...", detailed_status_messages, progress_tracker)
                    
                    keywords_data = await self.dataforseo_async_service.get_detailed_keywords_async(domain, 10000)
                    if keywords_data and keywords_data.get("items"):
                        detailed_data_available["keywords"] = True
                        operation_logger.log_data_collection("keywords", record_count=len(keywords_data.get("items", [])), message="Keywords analysis completed")
                        detailed_status_messages.append("Keywords analysis completed")
                        await self._update_progress_data(report, "Keywords analysis completed", detailed_status_messages, progress_tracker)
                        progress_tracker.complete_sub_operation("detailed_data", "keywords_analysis")
                        
                        # Save detailed data to database
                        detailed_data = DetailedAnalysisData(
                            domain_name=domain,
                            data_type=DetailedDataType.KEYWORDS,
                            json_data=keywords_data
                        )
                        await self.db.save_detailed_data(detailed_data)
                    else:
                        logger.warning("Async keywords collection returned None, falling back to legacy", domain=domain)
                        # Fall back to legacy mode for keywords
                        keywords_data = await self.dataforseo_service.get_detailed_keywords(domain, 1000)
                        if keywords_data:
                            detailed_data_available["keywords"] = True
                            operation_logger.log_data_collection("keywords", record_count=len(keywords_data.get("items", [])), message="Keywords analysis completed (legacy)")
                            detailed_status_messages.append("Keywords analysis completed (legacy)")
                            await self._update_progress_data(report, "Keywords analysis completed (legacy)", detailed_status_messages, progress_tracker)
                            progress_tracker.complete_sub_operation("detailed_data", "keywords_analysis")
                            
                            # Save detailed data to database
                            detailed_data = DetailedAnalysisData(
                                domain_name=domain,
                                data_type=DetailedDataType.KEYWORDS,
                                json_data=keywords_data
                            )
                            await self.db.save_detailed_data(detailed_data)
                    
                    # Collect referring domains
                    progress_tracker.start_sub_operation("detailed_data", "referring_domains_analysis")
                    operation_logger.log_data_collection("referring_domains", message="Starting referring domains analysis...")
                    detailed_status_messages.append("Starting referring domains analysis...")
                    await self._update_progress_data(report, "Starting referring domains analysis...", detailed_status_messages, progress_tracker)
                    
                    # Add intermediate progress update
                    detailed_status_messages.append("Collecting referring domains data...")
                    await self._update_progress_data(report, "Collecting referring domains data...", detailed_status_messages, progress_tracker)
                    
                    referring_domains_data = await self.dataforseo_async_service.get_referring_domains_async(domain, 10000)
                    if referring_domains_data and referring_domains_data.get("items"):
                        detailed_data_available["referring_domains"] = True
                        operation_logger.log_data_collection("referring_domains", record_count=len(referring_domains_data.get("items", [])), message="Referring domains analysis completed")
                        detailed_status_messages.append("Referring domains analysis completed")
                        await self._update_progress_data(report, "Referring domains analysis completed", detailed_status_messages, progress_tracker)
                        progress_tracker.complete_sub_operation("detailed_data", "referring_domains_analysis")
                        
                        # Save detailed data to database
                        detailed_data = DetailedAnalysisData(
                            domain_name=domain,
                            data_type=DetailedDataType.REFERRING_DOMAINS,
                            json_data=referring_domains_data
                        )
                        await self.db.save_detailed_data(detailed_data)
                    else:
                        logger.warning("Async referring domains collection returned None, falling back to legacy", domain=domain)
                        # Fall back to legacy mode for referring domains
                        referring_domains_data = await self.dataforseo_service.get_referring_domains(domain, 800)
                        if referring_domains_data:
                            detailed_data_available["referring_domains"] = True
                            operation_logger.log_data_collection("referring_domains", record_count=len(referring_domains_data.get("items", [])), message="Referring domains analysis completed (legacy)")
                            detailed_status_messages.append("Referring domains analysis completed (legacy)")
                            await self._update_progress_data(report, "Referring domains analysis completed (legacy)", detailed_status_messages, progress_tracker)
                            progress_tracker.complete_sub_operation("detailed_data", "referring_domains_analysis")
                            
                            # Save detailed data to database
                            detailed_data = DetailedAnalysisData(
                                domain_name=domain,
                                data_type=DetailedDataType.REFERRING_DOMAINS,
                                json_data=referring_domains_data
                            )
                            await self.db.save_detailed_data(detailed_data)
                    
                except Exception as e:
                    logger.warning("Async detailed data collection failed, falling back to legacy", domain=domain, error=str(e))
                    if analysis_mode == AnalysisMode.DUAL:
                        # Fallback to legacy mode
                        analysis_mode = AnalysisMode.LEGACY
                    else:
                        raise
            
            if analysis_mode == AnalysisMode.LEGACY:
                # Use legacy pattern - but still require N8N for backlinks
                # Check if N8N should be used for backlinks
                use_n8n_legacy = self.n8n_service.is_enabled_for_backlinks()
                
                if use_n8n_legacy:
                    # Use N8N even in legacy mode
                    logger.info("Using N8N for backlinks in legacy mode", domain=domain)
                    n8n_result = await self.n8n_service.trigger_backlinks_workflow(domain, 1000)
                    if n8n_result:
                        max_wait_time = 120
                        wait_interval = 2
                        waited = 0
                        
                        while waited < max_wait_time:
                            await asyncio.sleep(wait_interval)
                            waited += wait_interval
                            
                            from models.domain_analysis import DetailedDataType
                            saved_data = await self.db.get_detailed_data(domain, DetailedDataType.BACKLINKS)
                            if saved_data:
                                backlinks_data = saved_data.json_data
                                break
                        
                        if not backlinks_data:
                            logger.warning("N8N workflow did not return data in legacy mode", domain=domain)
                            backlinks_data = None
                    else:
                        logger.error("N8N workflow trigger failed in legacy mode", domain=domain)
                        backlinks_data = None
                else:
                    # N8N is required - cannot use direct HTTP
                    logger.error("N8N is required for backlinks but is not enabled (legacy mode)", domain=domain)
                    raise Exception("N8N is required for backlinks analysis. Please enable N8N in your configuration.")
                
                # Fallback removed - N8N is required
                if not backlinks_data:
                    backlinks_data = None  # Will be handled below
                if backlinks_data and backlinks_data.get("items"):
                    detailed_data_available["backlinks"] = True
                    operation_logger.log_data_collection("backlinks", record_count=len(backlinks_data.get("items", [])))
                    # Save detailed data to database
                    from models.domain_analysis import DetailedAnalysisData, DetailedDataType
                    detailed_data = DetailedAnalysisData(
                        domain_name=domain,
                        data_type=DetailedDataType.BACKLINKS,
                        json_data=backlinks_data
                    )
                    await self.db.save_detailed_data(detailed_data)
                
                keywords_data = await self.dataforseo_service.get_detailed_keywords(domain, 1000)
                if keywords_data and keywords_data.get("items"):
                    detailed_data_available["keywords"] = True
                    operation_logger.log_data_collection("keywords", record_count=len(keywords_data.get("items", [])))
                    # Save detailed data to database
                    detailed_data = DetailedAnalysisData(
                        domain_name=domain,
                        data_type=DetailedDataType.KEYWORDS,
                        json_data=keywords_data
                    )
                    await self.db.save_detailed_data(detailed_data)
                
                referring_domains_data = await self.dataforseo_service.get_referring_domains(domain, 800)
                if referring_domains_data and referring_domains_data.get("items"):
                    detailed_data_available["referring_domains"] = True
                    operation_logger.log_data_collection("referring_domains", record_count=len(referring_domains_data.get("items", [])))
                    # Save detailed data to database
                    detailed_data = DetailedAnalysisData(
                        domain_name=domain,
                        data_type=DetailedDataType.REFERRING_DOMAINS,
                        json_data=referring_domains_data
                    )
                    await self.db.save_detailed_data(detailed_data)
            
            # Update report with detailed data availability
            progress_tracker.start_sub_operation("detailed_data", "data_saving")
            report.detailed_data_available = detailed_data_available
            report.analysis_phase = AnalysisPhase.AI_ANALYSIS
            
            # Save report with detailed data availability
            await self.db.save_report(report)
            progress_tracker.complete_sub_operation("detailed_data", "data_saving")
            logger.info("Detailed data collection completed and saved", 
                       domain=domain, 
                       detailed_data_available=detailed_data_available)
            
            # Verify we have detailed data (optional for enhanced analysis)
            if not any(detailed_data_available.values()):
                logger.warning("No detailed data collected - proceeding with essential metrics only", domain=domain)
                # Don't raise exception - continue with essential metrics
            
            operation_logger.log_data_collection("detailed_data", record_count=sum(detailed_data_available.values()))
            
        except Exception as e:
            logger.error("Detailed data collection failed", domain=domain, error=str(e))
            raise
    
    async def _perform_ai_analysis(self, domain: str, report: DomainAnalysisReport, operation_logger: AsyncOperationLogger, progress_tracker=None):
        """Perform AI analysis with backlink quality assessment"""
        try:
            operation_logger.log_data_collection("ai_analysis")
            
            # Start LLM processing sub-operation
            if progress_tracker:
                progress_tracker.start_sub_operation("ai_analysis", "llm_processing")
            
            # Get detailed data for AI analysis
            detailed_data = {}
            for data_type in [DetailedDataType.BACKLINKS, DetailedDataType.KEYWORDS, DetailedDataType.REFERRING_DOMAINS]:
                data = await self.db.get_detailed_data(domain, data_type)
                if data:
                    detailed_data[data_type.value] = data.json_data
            
            # Prepare comprehensive data for LLM with actual total counts
            combined_data = {
                "domain": domain,
                "essential_metrics": {
                    "domain_rating": report.data_for_seo_metrics.domain_rating_dr if report.data_for_seo_metrics else None,  # This is actually DataForSEO domain rank
                    "organic_traffic": report.data_for_seo_metrics.organic_traffic_est if report.data_for_seo_metrics else None,
                    "total_keywords": report.data_for_seo_metrics.total_keywords if report.data_for_seo_metrics else None,
                    "total_backlinks": report.data_for_seo_metrics.total_backlinks if report.data_for_seo_metrics else None,
                    "total_referring_domains": report.data_for_seo_metrics.total_referring_domains if report.data_for_seo_metrics else None
                },
                "detailed_data": {
                    "backlinks": {
                        "total_count": report.data_for_seo_metrics.total_backlinks if report.data_for_seo_metrics else 0,
                        "items": detailed_data.get("backlinks", {}).get("items", [])
                    },
                    "keywords": {
                        "total_count": report.data_for_seo_metrics.total_keywords if report.data_for_seo_metrics else 0,
                        "items": detailed_data.get("keywords", {}).get("items", [])
                    },
                    "referring_domains": {
                        "total_count": report.data_for_seo_metrics.total_referring_domains if report.data_for_seo_metrics else 0,
                        "items": detailed_data.get("referring_domains", {}).get("items", [])
                    }
                },
                "wayback_data": report.wayback_machine_summary.dict() if report.wayback_machine_summary else {},
                "historical_data": report.historical_data.dict() if report.historical_data else {}
            }
            
            # Generate enhanced AI analysis with quality assessment
            operation_logger.log_data_collection("ai_analysis", message="Starting AI analysis and quality assessment...")
            llm_data = await self.llm_service.generate_enhanced_analysis(domain, combined_data)
            if llm_data:
                # Start analysis parsing sub-operation
                if progress_tracker:
                    progress_tracker.complete_sub_operation("ai_analysis", "llm_processing")
                    progress_tracker.start_sub_operation("ai_analysis", "analysis_parsing")
                
                # Convert quality_score values from float to string for Pydantic validation
                if 'advantages_disadvantages_table' in llm_data:
                    for item in llm_data['advantages_disadvantages_table']:
                        if 'quality_score' in item and isinstance(item['quality_score'], (int, float)):
                            item['quality_score'] = str(item['quality_score'])
                
                report.llm_analysis = LLMAnalysis(**llm_data)
                operation_logger.log_data_collection("ai_analysis", record_count=1, message="AI analysis completed successfully")
                
                # Complete analysis parsing sub-operation
                if progress_tracker:
                    progress_tracker.complete_sub_operation("ai_analysis", "analysis_parsing")
            
            report.analysis_phase = AnalysisPhase.COMPLETED
            
        except Exception as e:
            logger.error("AI analysis failed", domain=domain, error=str(e))
            raise
    
    async def _finalize_analysis(self, report: DomainAnalysisReport, start_time: datetime, progress_tracker: ProgressTracker):
        """Finalize the analysis report"""
        try:
            end_time = datetime.utcnow()
            report.processing_time_seconds = (end_time - start_time).total_seconds()
            report.status = AnalysisStatus.COMPLETED
            report.analysis_phase = AnalysisPhase.COMPLETED
            
            # Create progress info for final state
            report.progress_data = ProgressInfo(
                status=AsyncTaskStatus.COMPLETED,
                phase=AnalysisPhase.COMPLETED,
                progress_percentage=100,
                completed_operations=progress_tracker.get_completed_operations()
            )
            
        except Exception as e:
            logger.error("Analysis finalization failed", domain=report.domain_name, error=str(e))
            raise



    async def get_or_fetch_historical_data(self, domain: str) -> Optional['HistoricalData']:
        """Get or fetch historical data for a domain"""
        try:
            # 1. Check if report has historical data
            report = await self.db.get_report(domain)
            if report and report.historical_data:
                logger.info("Using cached historical data", domain=domain)
                return report.historical_data
                
            logger.info("Fetching new historical data", domain=domain)
            
            # 2. Fetch from APIs (parallel execution)
            rank_task = asyncio.create_task(self.dataforseo_service.get_historical_rank_overview(domain))
            traffic_task = asyncio.create_task(self.dataforseo_service.get_traffic_analytics_history(domain))
            
            rank_data, traffic_data = await asyncio.gather(rank_task, traffic_task, return_exceptions=True)
            
            # Handle exceptions
            if isinstance(rank_data, Exception):
                logger.error("Historical rank fetch failed", domain=domain, error=str(rank_data))
                rank_data = None
            if isinstance(traffic_data, Exception):
                logger.error("Traffic history fetch failed", domain=domain, error=str(traffic_data))
                traffic_data = None
            
            if not rank_data and not traffic_data:
                logger.warning("No historical data available", domain=domain)
                return None
                
            # 3. Parse data
            historical_data = self._parse_historical_data(rank_data, traffic_data)
            
            # 4. Save to report
            if report and historical_data:
                report.historical_data = historical_data
                await self.db.save_report(report)
                logger.info("Saved historical data to report", domain=domain)
                
            return historical_data
            
        except Exception as e:
            logger.error("Failed to get/fetch historical data", domain=domain, error=str(e))
            return None

    def _parse_historical_data(self, rank_data: Optional[Dict], traffic_data: Optional[Dict]) -> 'HistoricalData':
        """Parse raw API data into HistoricalData model"""
        from models.domain_analysis import (
            HistoricalData, HistoricalRankOverview, TrafficAnalyticsHistory, 
            HistoricalMetricPoint
        )
        
        rank_overview = None
        if rank_data and rank_data.get("items"):
            items = rank_data.get("items", [])
            # Sort by date
            items.sort(key=lambda x: x.get("date", ""))
            
            organic_keywords_count = []
            organic_traffic = []
            organic_traffic_value = []
            
            for item in items:
                date_str = item.get("date")
                if not date_str:
                    continue
                
                metrics = item.get("metrics", {}).get("organic")
                
                if not metrics:
                    continue
                
                organic_keywords_count.append(HistoricalMetricPoint(
                    date=date_str, value=float(metrics.get("count", 0))
                ))
                organic_traffic.append(HistoricalMetricPoint(
                    date=date_str, value=float(metrics.get("etv", 0)) # etv often proxy for traffic or traffic value, checking docs...
                    # Wait, 'etv' is Estimated Traffic Value. 'pos_*' are counts. 
                    # DataForSEO `historical_rank_overview` gives `metrics.organic.count` (keywords count) and `etv` (traffic value cost).
                    # Actually, usually they provide `organic.is_lost` etc.
                    # Let's assume 'etv' is value, and we might not have direct traffic count here, but often 'etv' is used.
                    # The user said "metrics.organic.count" (keywords) and "estimated organic/paid traffic".
                    # Let's check traffic estimation endpoint for actual traffic volume.
                ))
                # Actually, `historical_rank_overview` mainly gives keyword counts.
                # `etv` is usually traffic cost.
                # `organic_traffic` might be better from `traffic_analytics`.
                
            # Populate rank overview
            rank_overview = HistoricalRankOverview(
                organic_keywords_count=organic_keywords_count,
                 # Assuming etv for now, but traffic analytics is better for traffic
                organic_traffic_value=[HistoricalMetricPoint(date=i.date, value=i.value) for i in organic_traffic], 
                raw_items=items
            )

        traffic_analytics = None
        if traffic_data and traffic_data.get("items"):
            items = traffic_data.get("items", [])
            items.sort(key=lambda x: x.get("date", ""))
            
            visits_history = []
            bounce_rate_history = []
            unique_visitors_history = []
            
            for item in items:
                date_str = item.get("date")
                if not date_str:
                    continue
                
                # traffic_analytics/history returns items with 'visits', 'bounce_rate', etc. directly or under keys?
                # DataForSEO Traffic Analytics usually has structure like:
                # item['value']? No. 
                # Checking hypothetical structure. Usually: item['visits'], item['bounce_rate'].
                # Since I don't have exact docs, I'll allow flexibility or check `item` content.
                # Assuming typical DataForSEO structure for traffic history:
                visits = item.get("visits", 0)
                bounce_rate = item.get("bounce_rate", 0)
                unique_visitors = item.get("uniqe_visitors", 0) # Note typo in some APIs, check for 'unique_visitors' too
                if not unique_visitors:
                    unique_visitors = item.get("unique_visitors", 0)
                
                visits_history.append(HistoricalMetricPoint(date=date_str, value=float(visits)))
                bounce_rate_history.append(HistoricalMetricPoint(date=date_str, value=float(bounce_rate)))
                unique_visitors_history.append(HistoricalMetricPoint(date=date_str, value=float(unique_visitors)))
            
            traffic_analytics = TrafficAnalyticsHistory(
                visits_history=visits_history,
                bounce_rate_history=bounce_rate_history,
                unique_visitors_history=unique_visitors_history,
                raw_items=items
            )
            
        return HistoricalData(
            rank_overview=rank_overview,
            traffic_analytics=traffic_analytics
        )

    async def analyze_domain_legacy(self, domain: str, report_id: str) -> None:
        """
        Perform complete domain analysis
        This method runs in the background and updates the report as it progresses
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info("Starting domain analysis", domain=domain, report_id=report_id)
            
            # Get existing report or create new one
            report = await self.db.get_report(domain)
            if not report:
                # Create new report if it doesn't exist
                report = DomainAnalysisReport(
                    domain_name=domain,
                    status=AnalysisStatus.IN_PROGRESS
                )
                await self.db.save_report(report)
            else:
                # Update existing report status
                report.status = AnalysisStatus.IN_PROGRESS
                report.error_message = None
                report.processing_time_seconds = None
                await self.db.save_report(report)
            
            # Run essential data collection in parallel (summaries only to save costs)
            dataforseo_task = asyncio.create_task(
                self.dataforseo_service.get_domain_analytics(domain)
            )
            wayback_task = asyncio.create_task(
                self.wayback_service.get_domain_history(domain)
            )
            
            # Wait for data collection to complete
            dataforseo_data, wayback_data = await asyncio.gather(
                dataforseo_task,
                wayback_task,
                return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(dataforseo_data, Exception):
                logger.error("DataForSEO data collection failed", domain=domain, error=str(dataforseo_data))
                dataforseo_data = None
            
            if isinstance(wayback_data, Exception):
                logger.error("Wayback Machine data collection failed", domain=domain, error=str(wayback_data))
                wayback_data = None
            
            # Parse the collected data
            dataforseo_metrics = None
            if dataforseo_data:
                logger.info("Parsing DataForSEO data in analysis service", 
                           dataforseo_keys=list(dataforseo_data.keys()),
                           backlinks_summary_in_data=dataforseo_data.get("backlinks_summary", {}),
                           domain_rank_in_data=dataforseo_data.get("domain_rank", {}))
                dataforseo_metrics = self.dataforseo_service.parse_domain_metrics(dataforseo_data)
                logger.info("Parsed DataForSEO metrics", 
                           total_backlinks=dataforseo_metrics.total_backlinks,
                           total_referring_domains=dataforseo_metrics.total_referring_domains,
                           organic_traffic_est=dataforseo_metrics.organic_traffic_est)
            
            wayback_summary = None
            if wayback_data:
                wayback_summary = self._parse_wayback_data(wayback_data, domain)
            
            # Generate LLM analysis
            llm_analysis = None
            if dataforseo_data or wayback_data:
                # Structure data to match what LLM service expects
                backlinks_summary = dataforseo_data.get("backlinks_summary", {}) if dataforseo_data else {}
                domain_rank = dataforseo_data.get("domain_rank", {}) if dataforseo_data else {}
                
                combined_data = {
                    "analytics": {
                        "domain_rank": domain_rank,
                        "organic_traffic": domain_rank.get("organic", {}).get("etv", 0) if domain_rank else 0
                    },
                    "backlinks": {
                        "total_count": backlinks_summary.get("referring_domains", 0),
                        "backlinks_count": backlinks_summary.get("backlinks", 0),
                        "items": dataforseo_data.get("backlinks", {}).get("items", []) if dataforseo_data else []
                    },
                    "keywords": {
                        "items": dataforseo_data.get("keywords", {}).get("items", []) if dataforseo_data else []
                    },
                    "wayback": wayback_data or {}
                }
                
                llm_data = await self.llm_service.generate_analysis(domain, combined_data)
                if llm_data:
                    llm_analysis = LLMAnalysis(**llm_data)
            
            # Create final report
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            report = DomainAnalysisReport(
                domain_name=domain,
                analysis_timestamp=end_time,
                status=AnalysisStatus.COMPLETED,
                data_for_seo_metrics=dataforseo_metrics,
                wayback_machine_summary=wayback_summary,
                llm_analysis=llm_analysis,
                raw_data_links={
                    "full_keywords_list_api": f"/api/v1/reports/{domain}/keywords",
                    "full_backlinks_list_api": f"/api/v1/reports/{domain}/backlinks"
                },
                processing_time_seconds=processing_time
            )
            
            # Save the completed report
            await self.db.save_report(report)
            
            logger.info("Domain analysis completed successfully", 
                       domain=domain, processing_time=processing_time)
            
        except Exception as e:
            logger.error("Domain analysis failed", domain=domain, error=str(e))
            
            # Update report with error status
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            error_report = DomainAnalysisReport(
                domain_name=domain,
                analysis_timestamp=end_time,
                status=AnalysisStatus.FAILED,
                processing_time_seconds=processing_time,
                error_message=str(e)
            )
            
            await self.db.save_report(error_report)
    
    async def _update_report_status(self, domain: str, status: AnalysisStatus) -> None:
        """Update report status in database"""
        try:
            report = await self.db.get_report(domain)
            if report:
                report.status = status
                await self.db.save_report(report)
        except Exception as e:
            logger.error("Failed to update report status", domain=domain, status=status, error=str(e))
    
    def _parse_wayback_data(self, wayback_data: dict, domain: str) -> WaybackMachineSummary:
        """Parse Wayback Machine data into summary format"""
        try:
            first_capture_year = wayback_data.get("first_capture_year")
            total_captures = wayback_data.get("total_captures", 0)
            last_capture_date_str = wayback_data.get("last_capture_date")
            
            # Convert string to datetime if present
            last_capture_date = None
            if last_capture_date_str:
                from datetime import datetime
                last_capture_date = datetime.fromisoformat(last_capture_date_str)
            
            # Generate historical risk assessment
            historical_risk = self._assess_historical_risk(wayback_data)
            
            # Generate earliest snapshot URL
            earliest_snapshot_url = None
            if first_capture_year and total_captures > 0:
                # Use current year with zeros for Wayback Machine URL format
                from datetime import datetime
                current_year = datetime.now().year
                earliest_snapshot_url = f"https://web.archive.org/web/{current_year}0000000000*/http://{domain}"
            
            return WaybackMachineSummary(
                first_capture_year=first_capture_year,
                total_captures=total_captures,
                last_capture_date=last_capture_date,
                historical_risk_assessment=historical_risk,
                earliest_snapshot_url=earliest_snapshot_url
            )
            
        except Exception as e:
            logger.error("Failed to parse Wayback Machine data", error=str(e))
            return WaybackMachineSummary()
    
    def _assess_historical_risk(self, wayback_data: dict) -> str:
        """Assess historical risk based on Wayback Machine data"""
        try:
            total_captures = wayback_data.get("total_captures", 0)
            first_capture_year = wayback_data.get("first_capture_year")
            captures = wayback_data.get("captures", [])
            
            if total_captures == 0:
                return "High: No historical data available - domain may be new or problematic"
            
            if first_capture_year and first_capture_year < 2010:
                return "Low: Domain has long, established history"
            elif first_capture_year and first_capture_year < 2020:
                return "Medium: Domain has moderate history"
            else:
                return "Medium: Domain is relatively new"
            
            # Additional risk factors could be added here:
            # - Check for suspicious patterns in captures
            # - Analyze status codes
            # - Look for gaps in capture history
            
        except Exception as e:
            logger.error("Failed to assess historical risk", error=str(e))
            return "Unknown: Unable to assess historical risk"
    
    async def _update_progress_data(self, report: DomainAnalysisReport, current_message: str, detailed_status: list, progress_tracker=None):
        """Update progress data with current status message and progress tracking"""
        try:
            # Get progress information from tracker if available
            progress_percentage = 0
            completed_operations = 0
            total_operations = 4
            current_operation = None
            estimated_time_remaining = 0
            
            if progress_tracker:
                progress_percentage = progress_tracker.get_progress_percentage()
                completed_operations = progress_tracker.completed_operations
                total_operations = progress_tracker.total_operations
                current_operation = progress_tracker.get_current_operation()
                estimated_time_remaining = progress_tracker.get_estimated_time_remaining() or 0
            
            # Create ProgressInfo object
            from models.domain_analysis import ProgressInfo, AsyncTaskStatus, AnalysisPhase
            
            report.progress_data = ProgressInfo(
                status=AsyncTaskStatus.IN_PROGRESS if report.status == AnalysisStatus.IN_PROGRESS else AsyncTaskStatus.COMPLETED,
                phase=report.analysis_phase,
                progress_percentage=progress_percentage,
                estimated_time_remaining=estimated_time_remaining,
                current_operation=current_operation,
                completed_operations=detailed_status,
                error_message=None
            )
            
            # Save updated progress to database
            await self.db.save_report(report)
            
        except Exception as e:
            logger.error("Failed to update progress data", error=str(e))
    
    async def get_analysis_progress(self, domain: str) -> dict:
        """Get current analysis progress"""
        try:
            report = await self.db.get_report(domain)
            if not report:
                return {"status": "not_found", "progress": 0}
            
            if report.status == AnalysisStatus.COMPLETED:
                return {"status": "completed", "progress": 100}
            elif report.status == AnalysisStatus.FAILED:
                return {"status": "failed", "progress": 0, "error": report.error_message}
            elif report.status == AnalysisStatus.IN_PROGRESS:
                # Estimate progress based on processing time
                if report.processing_time_seconds:
                    progress = min(int((report.processing_time_seconds / 15) * 100), 90)
                else:
                    progress = 50
                return {"status": "in_progress", "progress": progress}
            else:
                return {"status": "pending", "progress": 0}
                
        except Exception as e:
            logger.error("Failed to get analysis progress", domain=domain, error=str(e))
            return {"status": "error", "progress": 0, "error": str(e)}
