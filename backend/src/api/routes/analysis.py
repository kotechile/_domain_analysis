"""
Domain analysis API routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from middleware.auth_middleware import get_current_user
from typing import Optional
import structlog
import asyncio
from datetime import datetime

from models.domain_analysis import ( DomainAnalysisRequest, AnalysisResponse, DomainAnalysisReport, AnalysisStatus, AnalysisMode, AnalysisPhase, DetailedDataType, ProgressInfo )
from services.analysis_service import AnalysisService
from services.database import get_database
from services.pricing_service import PricingService
from services.credits_service import CreditsService
from services.usage_tracking import UsageTrackingService

logger = structlog.get_logger()
router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_domain( request: DomainAnalysisRequest, background_tasks: BackgroundTasks, current_user = Depends(get_current_user) ):
    """
    Start domain analysis process
    Returns immediately with analysis ID, actual analysis runs in background
    """
    try:
        analysis_service = AnalysisService()
        db = get_database()
        
        # Check if analysis already exists
        existing_report = await db.get_report(request.domain)
        if existing_report:
            # If same mode or higher mode exists, return existing
            if existing_report.status == AnalysisStatus.COMPLETED:
                # If existing is DUAL or matches requested mode, return it
                if existing_report.analysis_mode == request.mode or existing_report.analysis_mode == AnalysisMode.DUAL:
                    return AnalysisResponse( success=True, message="Analysis already exists for this domain", report_id=request.domain )
            elif existing_report.status == AnalysisStatus.IN_PROGRESS:
                return AnalysisResponse( success=True, message="Analysis already in progress for this domain", report_id=request.domain )
        
        # Initialize pricing and credits services
        pricing_service = PricingService()
        credits_service = CreditsService(db)
        
        # Determine action and cost
        # Map LEGACY mode to ai_domain_summary, DUAL/ASYNC to deep_content_analysis
        action_name = "ai_domain_summary" if request.mode == AnalysisMode.LEGACY else "deep_content_analysis"
        logger.info("Calculating cost", action=action_name, user_id=str(current_user.id))
        cost = await pricing_service.calculate_action_cost(action_name)
        
        # Check balance
        logger.info("Checking balance", user_id=str(current_user.id), cost=cost)
        balance = await credits_service.get_balance(current_user.id)
        if balance < cost:
            logger.warning("Insufficient credits", user_id=str(current_user.id), balance=balance, cost=cost)
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient credits. Analysis cost: {cost}, Balance: {balance}"
            )
            
        # Deduct credits
        logger.info("Deducting credits", user_id=str(current_user.id), cost=cost)
        description = f"AI Domain Analysis: {request.domain} ({request.mode.value})"
        success = await credits_service.deduct_credits(current_user.id, cost, description, f"analysis_{request.domain}")
        if not success:
            logger.error("Credit deduction failed", user_id=str(current_user.id))
            raise HTTPException(status_code=402, detail="Insufficient credits or credit deduction failed")

        if existing_report:
            # Update existing report fields to pending
            existing_report.status = AnalysisStatus.PENDING
            existing_report.analysis_phase = AnalysisPhase.ESSENTIAL
            existing_report.analysis_timestamp = datetime.utcnow()
            existing_report.error_message = None
            existing_report.processing_time_seconds = None
            # Update the record
            await db.save_report(existing_report)
            report_id = existing_report.id if hasattr(existing_report, 'id') else request.domain
        else:
            # Create a new report
            report = DomainAnalysisReport(
                domain_name=request.domain,
                status=AnalysisStatus.PENDING,
                analysis_phase=AnalysisPhase.ESSENTIAL,
                analysis_timestamp=datetime.utcnow()
            )
            report_id = await db.save_report(report)
        
        # Start background analysis
        background_tasks.add_task( analysis_service.analyze_domain, request.domain, report_id, request.mode.value, current_user.id )
        
        logger.info("Domain analysis started", domain=request.domain, mode=request.mode, report_id=report_id, user_id=current_user.id)
        
        return AnalysisResponse( success=True, message=f"Analysis started successfully ({'Summary' if action_name == 'ai_domain_summary' else 'Deep'})", report_id=report_id, estimated_completion_time=15 if action_name == "ai_domain_summary" else 45 )
        
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
            return AnalysisResponse( success=False, message=f"Analysis failed: {report.error_message}", report_id=domain )
        elif report.status == AnalysisStatus.COMPLETED:
            return AnalysisResponse( success=True, message="Analysis completed successfully", report_id=domain )
        else:
            return AnalysisResponse( success=True, message="Analysis in progress", report_id=domain )
        
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
async def retry_analysis( domain: str, background_tasks: BackgroundTasks, current_user = Depends(get_current_user) ):
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
        report.analysis_timestamp = datetime.utcnow()
        report.error_message = None
        report.processing_time_seconds = None
        
        report_id = await db.save_report(report)
        
        # Start background analysis
        background_tasks.add_task( analysis_service.analyze_domain, domain, report_id, "dual", current_user.id )
        
        logger.info("Analysis retry started", domain=domain, report_id=report_id)
        
        return AnalysisResponse( success=True, message="Analysis retry started successfully", report_id=report_id, estimated_completion_time=15 )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retry analysis", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retry analysis")


@router.post("/analyze/v2", response_model=AnalysisResponse)
async def analyze_domain_v2( request: DomainAnalysisRequest, mode: str = "dual" ):
    """
    Start domain analysis with dual-mode support
    """
    try:
        analysis_service = AnalysisService()
        
        # Start analysis with specified mode
        report = await analysis_service.analyze_domain(request.domain, mode=mode)
        
        return AnalysisResponse( success=True, message="Analysis completed successfully", report_id=report.domain_name, estimated_completion_time=int(report.processing_time_seconds) if report.processing_time_seconds else None )
        
    except Exception as e:
        logger.error("Failed to analyze domain", domain=request.domain, error=str(e))
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/analyze/{domain}/status")
async def get_analysis_status(domain: str, mode: str = "dual"):
    """
    Get analysis status with progress tracking
    """
    try:
        db = get_database()
        report = await db.get_report(domain)
        
        if not report:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        # Get detailed data availability
        detailed_data_available = {}
        for data_type in [DetailedDataType.BACKLINKS, DetailedDataType.KEYWORDS, DetailedDataType.REFERRING_DOMAINS]:
            data = await db.get_detailed_data(domain, data_type)
            detailed_data_available[data_type.value] = data is not None
        
        return { "success": True, "message": "Status retrieved successfully", "report_id": report.domain_name, "status": report.status.value, "analysis_phase": report.analysis_phase.value, "analysis_mode": report.analysis_mode.value, "detailed_data_available": detailed_data_available, "progress": report.progress_data.dict() if report.progress_data else None }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get analysis status", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get analysis status")


@router.get("/analyze/{domain}/detailed/{data_type}")
async def get_detailed_data(domain: str, data_type: str):
    """
    Get detailed analysis data (backlinks, keywords, referring domains)
    """
    try:
        # Validate data type
        try:
            data_type_enum = DetailedDataType(data_type)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid data type: {data_type}")
        
        db = get_database()
        detailed_data = await db.get_detailed_data(domain, data_type_enum)
        
        if not detailed_data:
            raise HTTPException(status_code=404, detail=f"Detailed {data_type} data not found")
        
        return { "success": True, "data": detailed_data.json_data, "metadata": { "domain": detailed_data.domain_name, "data_type": detailed_data.data_type.value, "created_at": detailed_data.created_at.isoformat() if detailed_data.created_at else None, "expires_at": detailed_data.expires_at.isoformat() if detailed_data.expires_at else None, "data_freshness": "fresh" if detailed_data.created_at and (datetime.utcnow() - detailed_data.created_at).total_seconds() < 86400 else "stale", "record_count": len(detailed_data.json_data.get("items", [])) } }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get detailed data", domain=domain, data_type=data_type, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get detailed data")


@router.get("/analyze/{domain}/progress")
async def get_analysis_progress(domain: str):
    """
    Get analysis progress information
    """
    try:
        db = get_database()
        report = await db.get_report(domain)
        
        if not report:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        if not report.progress_data:
            return { "success": True, "progress": { "status": report.status.value, "phase": report.analysis_phase.value, "progress_percentage": 100 if report.status == AnalysisStatus.COMPLETED else 0, "current_operation": None, "completed_operations": [], "estimated_time_remaining": None } }
        
        return { "success": True, "progress": report.progress_data.dict() }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get analysis progress", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get analysis progress")


@router.post("/analyze/{domain}/refresh")
async def refresh_analysis_data(domain: str, data_types: Optional[list] = None, force: bool = False, current_user = Depends(get_current_user)):
    """
    Manually refresh analysis data
    """
    try:
        analysis_service = AnalysisService()
        db = get_database()
        usage_tracking = UsageTrackingService()
        
        # Check if analysis exists
        report = await db.get_report(domain)
        if not report:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        # Determine which data types to refresh
        if not data_types:
            data_types = ["backlinks", "keywords", "referring_domains"]
        
        # Validate data types
        valid_data_types = []
        for dt in data_types:
            try:
                valid_data_types.append(DetailedDataType(dt))
            except ValueError:
                raise HTTPException(status_code=422, detail=f"Invalid data type: {dt}")
        
        # Refresh data
        refreshed_count = 0
        for data_type in valid_data_types:
            # Delete existing data if force refresh
            if force:
                await db.delete_detailed_data(domain, data_type)
            
            # Collect fresh data (methods return (data, cost) tuple)
            total_cost = 0.0
            if data_type == DetailedDataType.BACKLINKS:
                data, cost = await analysis_service.dataforseo_async_service.get_detailed_backlinks_async(domain, 1000)
                total_cost += cost
            elif data_type == DetailedDataType.KEYWORDS:
                data, cost = await analysis_service.dataforseo_async_service.get_detailed_keywords_async(domain, 1000)
                total_cost += cost
            elif data_type == DetailedDataType.REFERRING_DOMAINS:
                data, cost = await analysis_service.dataforseo_async_service.get_referring_domains_async(domain, 800)
                total_cost += cost
            
            if data:
                from models.domain_analysis import DetailedAnalysisData
                detailed_data = DetailedAnalysisData( domain_name=domain, data_type=data_type, json_data=data )
                await db.store_detailed_data(detailed_data)
                refreshed_count += 1

        # Track cost if any API calls were made
        if total_cost > 0:
            usage_tracker = UsageTrackingService()
            await usage_tracker.track_usage(
                user_id=None,  # System operation
                resource_type='dataforseo',
                operation='refresh_analysis_data',
                provider='dataforseo',
                model='v3',
                cost_estimated=total_cost,
                details={'domain': domain, 'data_types': [dt.value for dt in valid_data_types], 'refreshed_count': refreshed_count}
            )
            logger.info("DataForSEO cost tracked for refresh", domain=domain, cost=total_cost)

        return { "success": True, "message": f"Refreshed {refreshed_count} data types successfully", "refreshed_types": [dt.value for dt in valid_data_types], "refresh_id": f"refresh_{domain}_{int(datetime.utcnow().timestamp())}", "cost_tracked": total_cost }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to refresh analysis data", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to refresh analysis data")


@router.get("/reports/{domain}/progress")
async def get_analysis_progress(domain: str):
    """
    Get current analysis progress with detailed status messages
    """
    try:
        db = get_database()
        report = await db.get_report(domain)
        
        if not report:
            return { "success": False, "message": "Analysis not found", "progress": None }
        
        # Get progress data from the report
        progress_data = report.progress_data or {}
        
        # Get current phase and status
        current_phase = report.analysis_phase or "essential"
        current_status = report.status
        
        # Create progress response
        progress_info = { "domain": domain, "status": current_status, "phase": current_phase, "progress_percentage": progress_data.get("progress_percentage", 0), "current_operation": progress_data.get("current_operation", ""), "status_message": progress_data.get("status_message", ""), "completed_operations": progress_data.get("completed_operations", 0), "total_operations": progress_data.get("total_operations", 4), "estimated_time_remaining": progress_data.get("estimated_time_remaining", 0), "detailed_status": progress_data.get("detailed_status", []), "last_updated": report.analysis_timestamp.isoformat() if report.analysis_timestamp else None }
        
        return { "success": True, "message": "Progress retrieved successfully", "progress": progress_info }
        
    except Exception as e:
        logger.error("Failed to get analysis progress", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")
