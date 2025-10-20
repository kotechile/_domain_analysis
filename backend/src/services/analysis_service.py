"""
Main analysis service that orchestrates domain analysis
"""

import asyncio
from datetime import datetime
from typing import Optional
import structlog

from models.domain_analysis import (
    DomainAnalysisReport, 
    AnalysisStatus, 
    DataForSEOMetrics,
    WaybackMachineSummary,
    LLMAnalysis
)
from services.database import get_database
from services.external_apis import DataForSEOService, WaybackMachineService, LLMService

logger = structlog.get_logger()


class AnalysisService:
    """Main service for orchestrating domain analysis"""
    
    def __init__(self):
        self.dataforseo_service = DataForSEOService()
        self.wayback_service = WaybackMachineService()
        self.llm_service = LLMService()
        self.db = get_database()
    
    async def analyze_domain(self, domain: str, report_id: str) -> None:
        """
        Perform complete domain analysis
        This method runs in the background and updates the report as it progresses
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info("Starting domain analysis", domain=domain, report_id=report_id)
            
            # Update status to in progress
            await self._update_report_status(domain, AnalysisStatus.IN_PROGRESS)
            
            # Run all data collection in parallel
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
            if isinstance(dataforseo_task, Exception):
                logger.error("DataForSEO data collection failed", domain=domain, error=str(dataforseo_task))
                dataforseo_data = None
            
            if isinstance(wayback_task, Exception):
                logger.error("Wayback Machine data collection failed", domain=domain, error=str(wayback_task))
                wayback_data = None
            
            # Parse the collected data
            dataforseo_metrics = None
            if dataforseo_data:
                dataforseo_metrics = self.dataforseo_service.parse_domain_metrics(dataforseo_data)
            
            wayback_summary = None
            if wayback_data:
                wayback_summary = self._parse_wayback_data(wayback_data)
            
            # Generate LLM analysis
            llm_analysis = None
            if dataforseo_data or wayback_data:
                combined_data = {
                    "analytics": dataforseo_data.get("analytics", {}) if dataforseo_data else {},
                    "backlinks": dataforseo_data.get("backlinks", {}) if dataforseo_data else {},
                    "keywords": dataforseo_data.get("keywords", {}) if dataforseo_data else {},
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
    
    def _parse_wayback_data(self, wayback_data: dict) -> WaybackMachineSummary:
        """Parse Wayback Machine data into summary format"""
        try:
            first_capture_year = wayback_data.get("first_capture_year")
            total_captures = wayback_data.get("total_captures", 0)
            last_capture_date = wayback_data.get("last_capture_date")
            
            # Generate historical risk assessment
            historical_risk = self._assess_historical_risk(wayback_data)
            
            # Generate earliest snapshot URL
            earliest_snapshot_url = None
            if first_capture_year and total_captures > 0:
                earliest_snapshot_url = f"https://web.archive.org/web/{first_capture_year}0101000000*/http://{domain}"
            
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
