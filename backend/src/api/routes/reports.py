"""
Reports API routes
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import structlog

from models.domain_analysis import ReportResponse, DomainAnalysisReport
from services.database import get_database

logger = structlog.get_logger()
router = APIRouter()


@router.get("/reports/{domain}", response_model=ReportResponse)
async def get_report(domain: str):
    """
    Get complete domain analysis report
    """
    try:
        db = get_database()
        report = await db.get_report(domain)
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        if report.status != "completed":
            return ReportResponse(
                success=False,
                message=f"Report not ready. Status: {report.status}",
                report=None
            )
        
        logger.info("Report retrieved successfully", domain=domain)
        
        return ReportResponse(
            success=True,
            report=report,
            message="Report retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get report", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get report")


@router.get("/reports", response_model=List[DomainAnalysisReport])
async def list_reports(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None)
):
    """
    List domain analysis reports with pagination
    """
    try:
        db = get_database()
        
        # Build query
        query = db.client.table('reports').select('*')
        
        if status:
            query = query.eq('status', status)
        
        # Add pagination
        query = query.order('created_at', desc=True).range(offset, offset + limit - 1)
        
        result = query.execute()
        
        reports = []
        for report_data in result.data:
            report = DomainAnalysisReport(
                domain_name=report_data['domain_name'],
                analysis_timestamp=report_data['analysis_timestamp'],
                status=report_data['status'],
                data_for_seo_metrics=report_data.get('data_for_seo_metrics'),
                wayback_machine_summary=report_data.get('wayback_machine_summary'),
                llm_analysis=report_data.get('llm_analysis'),
                raw_data_links=report_data.get('raw_data_links'),
                processing_time_seconds=report_data.get('processing_time_seconds'),
                error_message=report_data.get('error_message')
            )
            reports.append(report)
        
        logger.info("Reports listed successfully", count=len(reports), limit=limit, offset=offset)
        
        return reports
        
    except Exception as e:
        logger.error("Failed to list reports", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list reports")


@router.get("/reports/{domain}/keywords")
async def get_domain_keywords(
    domain: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Get detailed keywords data for a domain
    """
    try:
        db = get_database()
        report = await db.get_report(domain)
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        if not report.data_for_seo_metrics or not report.data_for_seo_metrics.organic_keywords:
            raise HTTPException(status_code=404, detail="Keywords data not available")
        
        keywords = report.data_for_seo_metrics.organic_keywords
        total_count = len(keywords)
        
        # Apply pagination
        paginated_keywords = keywords[offset:offset + limit]
        
        return {
            "domain": domain,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "keywords": paginated_keywords
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get keywords", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get keywords")


@router.get("/reports/{domain}/backlinks")
async def get_domain_backlinks(
    domain: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Get detailed backlinks data for a domain
    """
    try:
        db = get_database()
        report = await db.get_report(domain)
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        if not report.data_for_seo_metrics or not report.data_for_seo_metrics.referring_domains_info:
            raise HTTPException(status_code=404, detail="Backlinks data not available")
        
        backlinks = report.data_for_seo_metrics.referring_domains_info
        total_count = len(backlinks)
        
        # Apply pagination
        paginated_backlinks = backlinks[offset:offset + limit]
        
        return {
            "domain": domain,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "backlinks": paginated_backlinks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get backlinks", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get backlinks")


@router.delete("/reports/{domain}")
async def delete_report(domain: str):
    """
    Delete domain analysis report
    """
    try:
        db = get_database()
        
        # Check if report exists
        report = await db.get_report(domain)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Delete report
        db.client.table('reports').delete().eq('domain_name', domain).execute()
        
        # Also delete cached raw data
        await db.delete_raw_data(domain, "dataforseo")
        await db.delete_raw_data(domain, "wayback_machine")
        
        logger.info("Report deleted successfully", domain=domain)
        
        return {"success": True, "message": "Report deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete report", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete report")
