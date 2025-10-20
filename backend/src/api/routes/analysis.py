"""
Domain analysis API routes
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Optional
import structlog
import asyncio
from datetime import datetime

from models.domain_analysis import (
    DomainAnalysisRequest, 
    AnalysisResponse, 
    DomainAnalysisReport,
    AnalysisStatus
)
from services.analysis_service import AnalysisService
from services.database import get_database

logger = structlog.get_logger()
router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_domain(
    request: DomainAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    Start domain analysis process
    Returns immediately with analysis ID, actual analysis runs in background
    """
    try:
        analysis_service = AnalysisService()
        db = get_database()
        
        # Check if analysis already exists
        existing_report = await db.get_report(request.domain)
        if existing_report and existing_report.status == AnalysisStatus.COMPLETED:
            return AnalysisResponse(
                success=True,
                message="Analysis already exists for this domain",
                report_id=request.domain
            )
        
        # Create initial report record
        report = DomainAnalysisReport(
            domain_name=request.domain,
            status=AnalysisStatus.PENDING
        )
        
        # Save initial report
        report_id = await db.save_report(report)
        
        # Start background analysis
        background_tasks.add_task(
            analysis_service.analyze_domain,
            request.domain,
            report_id
        )
        
        logger.info("Domain analysis started", domain=request.domain, report_id=report_id)
        
        return AnalysisResponse(
            success=True,
            message="Analysis started successfully",
            report_id=report_id,
            estimated_completion_time=15  # seconds
        )
        
    except Exception as e:
        logger.error("Failed to start domain analysis", domain=request.domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start analysis")


@router.get("/analyze/{domain}", response_model=AnalysisResponse)
async def get_analysis_status(domain: str):
    """
    Get analysis status and results
    """
    try:
        db = get_database()
        report = await db.get_report(domain)
        
        if not report:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        if report.status == AnalysisStatus.FAILED:
            return AnalysisResponse(
                success=False,
                message=f"Analysis failed: {report.error_message}",
                report_id=domain
            )
        elif report.status == AnalysisStatus.COMPLETED:
            return AnalysisResponse(
                success=True,
                message="Analysis completed successfully",
                report_id=domain
            )
        else:
            return AnalysisResponse(
                success=True,
                message="Analysis in progress",
                report_id=domain
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get analysis status", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get analysis status")


@router.delete("/analyze/{domain}")
async def cancel_analysis(domain: str):
    """
    Cancel ongoing analysis (if possible)
    """
    try:
        db = get_database()
        report = await db.get_report(domain)
        
        if not report:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        if report.status in [AnalysisStatus.COMPLETED, AnalysisStatus.FAILED]:
            raise HTTPException(status_code=400, detail="Analysis already completed")
        
        # Update status to failed
        report.status = AnalysisStatus.FAILED
        report.error_message = "Analysis cancelled by user"
        await db.save_report(report)
        
        logger.info("Analysis cancelled", domain=domain)
        
        return {"success": True, "message": "Analysis cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to cancel analysis", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to cancel analysis")


@router.post("/analyze/{domain}/retry")
async def retry_analysis(
    domain: str,
    background_tasks: BackgroundTasks
):
    """
    Retry failed analysis
    """
    try:
        analysis_service = AnalysisService()
        db = get_database()
        
        # Get existing report
        report = await db.get_report(domain)
        if not report:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        if report.status not in [AnalysisStatus.FAILED]:
            raise HTTPException(status_code=400, detail="Analysis is not in failed state")
        
        # Reset report for retry
        report.status = AnalysisStatus.PENDING
        report.error_message = None
        report.processing_time_seconds = None
        
        report_id = await db.save_report(report)
        
        # Start background analysis
        background_tasks.add_task(
            analysis_service.analyze_domain,
            domain,
            report_id
        )
        
        logger.info("Analysis retry started", domain=domain, report_id=report_id)
        
        return AnalysisResponse(
            success=True,
            message="Analysis retry started successfully",
            report_id=report_id,
            estimated_completion_time=15
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retry analysis", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retry analysis")
