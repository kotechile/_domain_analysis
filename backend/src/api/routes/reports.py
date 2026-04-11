"""
Reports API routes
"""

from fastapi import APIRouter, HTTPException, Query, Response, Depends
from fastapi.responses import StreamingResponse
from typing import Any, List, Optional
from datetime import datetime
import structlog
import io

from models.domain_analysis import ReportResponse, DomainAnalysisReport, HistoricalData, DataForSEOMetrics, DetailedDataType, LLMAnalysis
from services.database import get_database, DataSource
from services.external_apis import DataForSEOService
from services.pdf_service import PDFService
from services.analysis_service import AnalysisService
from services.report_display_service import (
    build_referring_domains_display,
    shape_backlink_items,
    shape_keyword_items,
    shape_referring_domain_items,
)
from utils.date_utils import parse_iso_datetime
from middleware.auth_middleware import get_current_user

logger = structlog.get_logger()
router = APIRouter()


def _get_user_id(current_user: Any) -> Optional[str]:
    if not current_user:
        return None
    if isinstance(current_user, dict):
        return current_user.get('id')
    return getattr(current_user, 'id', None)


async def _get_owned_report_or_404(domain: str, current_user: Any):
    user_id = _get_user_id(current_user)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    db = get_database()
    report = await db.get_report(domain, user_id=user_id)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return db, report


async def _hydrate_report_response(db, report: DomainAnalysisReport) -> DomainAnalysisReport:
    """Backfill report counts from relational data for older/stale report rows."""
    report_changed = False

    if not report.data_for_seo_metrics:
        report.data_for_seo_metrics = DataForSEOMetrics()
        report_changed = True

    if not report.detailed_data_available:
        report.detailed_data_available = {}
        report_changed = True

    try:
        keywords_result = await db.get_detailed_items(report.domain_name, DetailedDataType.KEYWORDS, 1, 0)
        backlinks_result = await db.get_detailed_items(report.domain_name, DetailedDataType.BACKLINKS, 1, 0)
        referring_domains_result = await db.get_derived_referring_domains(report.domain_name, 1, 0)

        if keywords_result["total_count"] > 0:
            report.detailed_data_available["keywords"] = True
            if (report.data_for_seo_metrics.total_keywords or 0) < keywords_result["total_count"]:
                report.data_for_seo_metrics.total_keywords = keywords_result["total_count"]
                report_changed = True

        if backlinks_result["total_count"] > 0:
            report.detailed_data_available["backlinks"] = True
            if (report.data_for_seo_metrics.total_backlinks or 0) < backlinks_result["total_count"]:
                report.data_for_seo_metrics.total_backlinks = backlinks_result["total_count"]
                report_changed = True

        if referring_domains_result["total_count"] > 0:
            report.detailed_data_available["referring_domains"] = True
            if (report.data_for_seo_metrics.total_referring_domains or 0) < referring_domains_result["total_count"]:
                report.data_for_seo_metrics.total_referring_domains = referring_domains_result["total_count"]
                report_changed = True
    except Exception as hydration_error:
        logger.warning(
            "Failed to hydrate report detail counts from relational data",
            domain=report.domain_name,
            error=str(hydration_error),
        )

    display_payload = report.display_payload or {}
    payload_keywords = (display_payload.get("keywords") or {}).get("items", [])
    payload_backlinks = (display_payload.get("backlinks") or {}).get("items", [])
    payload_referring_domains = (display_payload.get("referring_domains") or {}).get("items", [])

    if not payload_backlinks:
        try:
            raw_data = await db.get_raw_data(report.domain_name, DataSource.DATAFORSEO)
            raw_backlinks = (raw_data or {}).get("backlinks", {})
            raw_backlink_items = raw_backlinks.get("items", []) if isinstance(raw_backlinks, dict) else []
            if raw_backlink_items:
                shaped_backlinks = shape_backlink_items(raw_backlink_items)
                display_payload = {
                    **display_payload,
                    "backlinks": {
                        "total_count": raw_backlinks.get("total_count", len(shaped_backlinks)),
                        "items": shaped_backlinks,
                    },
                }
                report.display_payload = display_payload
                payload_backlinks = shaped_backlinks
        except Exception as hydration_error:
            logger.warning(
                "Failed to hydrate backlink display payload from raw cache",
                domain=report.domain_name,
                error=str(hydration_error),
            )

    if payload_keywords:
        report.detailed_data_available["keywords"] = True
        payload_keywords_total = (display_payload.get("keywords") or {}).get("total_count", len(payload_keywords))
        if (report.data_for_seo_metrics.total_keywords or 0) < payload_keywords_total:
            report.data_for_seo_metrics.total_keywords = (display_payload.get("keywords") or {}).get("total_count", len(payload_keywords))
            report_changed = True

    if payload_backlinks:
        report.detailed_data_available["backlinks"] = True
        payload_backlinks_total = (display_payload.get("backlinks") or {}).get("total_count", len(payload_backlinks))
        if (report.data_for_seo_metrics.total_backlinks or 0) < payload_backlinks_total:
            report.data_for_seo_metrics.total_backlinks = (display_payload.get("backlinks") or {}).get("total_count", len(payload_backlinks))
            report_changed = True

    if payload_referring_domains:
        report.detailed_data_available["referring_domains"] = True
        payload_refdomains_total = (display_payload.get("referring_domains") or {}).get("total_count", len(payload_referring_domains))
        if (report.data_for_seo_metrics.total_referring_domains or 0) < payload_refdomains_total:
            report.data_for_seo_metrics.total_referring_domains = (display_payload.get("referring_domains") or {}).get("total_count", len(payload_referring_domains))
            report_changed = True

    if report.historical_data and report.historical_data.rank_overview:
        rank_overview = report.historical_data.rank_overview
        if (
            not rank_overview.organic_traffic
            and rank_overview.raw_items
        ):
            try:
                from models.domain_analysis import HistoricalMetricPoint

                recovered_points = []
                for item in rank_overview.raw_items:
                    year = item.get("year")
                    month = item.get("month")
                    organic = item.get("metrics", {}).get("organic")
                    if not year or not month or not organic:
                        continue
                    recovered_points.append(
                        HistoricalMetricPoint(
                            date=f"{year}-{int(month):02d}-01",
                            value=float(organic.get("etv", 0)),
                        )
                    )

                if recovered_points:
                    recovered_points.sort(key=lambda point: point.date)
                    rank_overview.organic_traffic = recovered_points
                    if not rank_overview.organic_traffic_value:
                        rank_overview.organic_traffic_value = [
                            HistoricalMetricPoint(date=point.date, value=point.value)
                            for point in recovered_points
                        ]
            except Exception as hydration_error:
                logger.warning(
                    "Failed to recover traffic series from historical raw_items",
                    domain=report.domain_name,
                    error=str(hydration_error),
                )

    if (
        report.data_for_seo_metrics.organic_traffic_est in (None, 0)
        and report.historical_data
        and report.historical_data.rank_overview
        and report.historical_data.rank_overview.organic_traffic
    ):
        try:
            latest_traffic = sorted(
                report.historical_data.rank_overview.organic_traffic,
                key=lambda point: point.date,
            )[-1].value
            if latest_traffic > 0:
                report.data_for_seo_metrics.organic_traffic_est = latest_traffic
        except Exception as hydration_error:
            logger.warning(
                "Failed to hydrate traffic from historical data",
                domain=report.domain_name,
                error=str(hydration_error),
            )

    total_backlinks = report.data_for_seo_metrics.total_backlinks or 0
    total_referring_domains = report.data_for_seo_metrics.total_referring_domains or 0
    total_keywords = report.data_for_seo_metrics.total_keywords or 0
    confidence_score = (report.llm_analysis.confidence_score or 0) if report.llm_analysis else 0
    summary_text = (report.llm_analysis.summary or "").lower() if report.llm_analysis else ""

    ai_looks_stale = (
        report.llm_analysis is not None
        and total_backlinks > 0
        and (
            confidence_score <= 0.01
            or "0 backlinks" in summary_text
            or "no backlinks" in summary_text
        )
    )

    if ai_looks_stale:
        try:
            backlinks_data = await db.get_detailed_data(report.domain_name, DetailedDataType.BACKLINKS)
            keywords_data = await db.get_detailed_data(report.domain_name, DetailedDataType.KEYWORDS)

            fallback_analysis = _generate_fallback_analysis(
                report.domain_name,
                {
                    "analytics": {
                        "domain_rank": report.data_for_seo_metrics.domain_rating_dr or 0,
                        "organic_traffic": report.data_for_seo_metrics.organic_traffic_est or 0,
                    },
                    "backlinks_summary": {
                        "backlinks": total_backlinks,
                        "referring_domains": total_referring_domains,
                    },
                    "backlinks": {
                        "items": (backlinks_data.json_data if backlinks_data else {}).get("items", []),
                    },
                    "keywords": {
                        "items": (keywords_data.json_data if keywords_data else {}).get("items", []),
                    },
                    "wayback": report.wayback_machine_summary.dict() if report.wayback_machine_summary else {},
                },
                include_backlinks=True,
                include_keywords=total_keywords > 0,
            )
            report.llm_analysis = LLMAnalysis(**fallback_analysis)
            report_changed = True
        except Exception as ai_refresh_error:
            logger.warning(
                "Failed to refresh stale AI memo from hydrated metrics",
                domain=report.domain_name,
                error=str(ai_refresh_error),
            )

    if report_changed:
        try:
            await db.save_report(report)
        except Exception as save_error:
            logger.warning(
                "Failed to persist hydrated report fields",
                domain=report.domain_name,
                error=str(save_error),
            )

    return report


@router.get("/reports/{domain}", response_model=ReportResponse)
async def get_report(domain: str, current_user = Depends(get_current_user)):
    """
    Get complete domain analysis report
    """
    try:
        db, report = await _get_owned_report_or_404(domain, current_user)
        report = await _hydrate_report_response(db, report)
        
        if report.status != "completed":
            # Include error message if report failed
            if report.status == "failed" and report.error_message:
                return ReportResponse( success=False, message=f"Analysis failed: {report.error_message}", report=report ) # Include report so frontend can access error_message
            return ReportResponse( success=False, message=f"Report not ready. Status: {report.status}", report=report ) # Include report even if not completed so frontend can check status
        
        logger.info("Report retrieved successfully", domain=domain)
        
        return ReportResponse( success=True, report=report, message="Report retrieved successfully" )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get report", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get report")


@router.get("/reports/{domain}/page-summary")
async def get_page_summary(domain: str, current_user = Depends(get_current_user)):
    """
    Get page summary data (backlinks summary) from raw_data_cache for a domain
    This data is collected during individual domain analysis
    """
    try:
        db, _ = await _get_owned_report_or_404(domain, current_user)
        
        # Get cached DataForSEO data which contains backlinks_summary
        raw_data = await db.get_raw_data(domain, DataSource.DATAFORSEO)
        
        if not raw_data:
            raise HTTPException(status_code=404, detail="Page summary data not found for this domain")
        
        # Extract backlinks_summary from cached data
        backlinks_summary = raw_data.get("backlinks_summary")
        
        if not backlinks_summary:
            raise HTTPException(status_code=404, detail="Backlinks summary not found in cached data")
        
        logger.info("Page summary retrieved successfully", domain=domain)
        
        return { "success": True, "data": backlinks_summary, "message": "Page summary retrieved successfully" }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get page summary", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get page summary")


@router.get("/reports/{domain}/details")
async def get_report_details(
    domain: str,
    keywords_limit: int = Query(100, ge=1, le=1000),
    backlinks_limit: int = Query(100, ge=1, le=1000),
    keywords_offset: int = Query(0, ge=0),
    backlinks_offset: int = Query(0, ge=0),
    sections: Optional[str] = Query(None, description="Comma-separated list of sections: keywords,referring_domains,backlinks"),
    current_user = Depends(get_current_user),
):
    """
    Get a single authenticated payload for the report detail page.
    """
    try:
        db, report = await _get_owned_report_or_404(domain, current_user)

        from models.domain_analysis import DetailedDataType

        requested_sections = {
            section.strip()
            for section in (sections.split(",") if sections else ["keywords", "referring_domains", "backlinks"])
            if section.strip()
        }

        include_keywords = "keywords" in requested_sections
        include_backlinks = "backlinks" in requested_sections
        include_referring_domains = "referring_domains" in requested_sections

        def empty_section() -> dict:
            return {"total_count": 0, "items": []}

        async def resolve_section(
            data_type,
            include: bool,
            limit: int,
            offset: int,
            relational_shaper,
            payload_key: str,
        ) -> dict:
            if not include:
                return empty_section()

            try:
                relational_result = await db.get_detailed_items(domain, data_type, limit, offset)
            except Exception as rel_error:
                logger.warning(
                    "Falling back to JSONB detailed data after relational read failed",
                    domain=domain,
                    data_type=data_type.value,
                    error=str(rel_error),
                )
                relational_result = empty_section()

            if relational_result["items"]:
                logger.info(
                    "Report detail section resolved from relational data",
                    domain=domain,
                    section=payload_key,
                    total_count=relational_result["total_count"],
                    returned_count=len(relational_result["items"]),
                )
                return {
                    "total_count": relational_result["total_count"],
                    "items": relational_shaper(relational_result["items"]),
                }

            payload_section = (getattr(report, "display_payload", None) or {}).get(payload_key, {})
            payload_items = payload_section.get("items", [])
            if payload_items:
                logger.info(
                    "Report detail section resolved from display payload",
                    domain=domain,
                    section=payload_key,
                    total_count=payload_section.get("total_count", len(payload_items)),
                    returned_count=len(payload_items[offset:offset + limit]),
                )
                sliced_items = payload_items[offset:offset + limit]
                return {
                    "total_count": payload_section.get("total_count", len(payload_items)),
                    "items": sliced_items,
                }

            try:
                legacy_detailed_data = await db.get_detailed_data(domain, data_type)
                legacy_items = (legacy_detailed_data.json_data if legacy_detailed_data else {}).get("items", [])
                if legacy_items:
                    shaped_items = relational_shaper(legacy_items)
                    sliced_items = shaped_items[offset:offset + limit]
                    logger.info(
                        "Report detail section resolved from legacy detailed data",
                        domain=domain,
                        section=payload_key,
                        total_count=legacy_detailed_data.json_data.get("total_count", len(shaped_items)),
                        returned_count=len(sliced_items),
                    )
                    return {
                        "total_count": legacy_detailed_data.json_data.get("total_count", len(shaped_items)),
                        "items": sliced_items,
                    }
            except Exception as legacy_error:
                logger.warning(
                    "Legacy detailed-data fallback failed",
                    domain=domain,
                    section=payload_key,
                    error=str(legacy_error),
                )

            if data_type == DetailedDataType.BACKLINKS:
                try:
                    raw_data = await db.get_raw_data(domain, DataSource.DATAFORSEO)
                    raw_backlinks = (raw_data or {}).get("backlinks", {})
                    raw_items = raw_backlinks.get("items", []) if isinstance(raw_backlinks, dict) else []
                    if raw_items:
                        shaped_items = shape_backlink_items(raw_items)
                        sliced_items = shaped_items[offset:offset + limit]
                        logger.info(
                            "Report detail backlinks resolved from raw cache",
                            domain=domain,
                            total_count=raw_backlinks.get("total_count", len(shaped_items)),
                            returned_count=len(sliced_items),
                        )
                        return {
                            "total_count": raw_backlinks.get("total_count", len(shaped_items)),
                            "items": sliced_items,
                        }
                except Exception as raw_error:
                    logger.warning(
                        "Backlinks raw-cache fallback failed",
                        domain=domain,
                        error=str(raw_error),
                    )

            logger.warning(
                "Report detail section resolved empty",
                domain=domain,
                section=payload_key,
            )
            return empty_section()

        keywords_result = await resolve_section(
            DetailedDataType.KEYWORDS,
            include_keywords,
            keywords_limit,
            keywords_offset,
            shape_keyword_items,
            "keywords",
        )
        backlinks_result = await resolve_section(
            DetailedDataType.BACKLINKS,
            include_backlinks,
            backlinks_limit,
            backlinks_offset,
            shape_backlink_items,
            "backlinks",
        )
        if include_referring_domains:
            referring_domains_result = {
                "total_count": 0,
                "items": [],
            }
            try:
                derived_result = await db.get_derived_referring_domains(domain, backlinks_limit, backlinks_offset)
                if derived_result["items"]:
                    referring_domains_result = {
                        "total_count": derived_result["total_count"],
                        "items": shape_referring_domain_items(derived_result["items"]),
                    }
            except Exception as rel_error:
                logger.warning(
                    "Relational read failed for referring domains",
                    domain=domain,
                    error=str(rel_error),
                )
                try:
                    backlink_legacy_data = await db.get_detailed_data(domain, DetailedDataType.BACKLINKS)
                    backlink_legacy_items = (backlink_legacy_data.json_data if backlink_legacy_data else {}).get("items", [])
                    if backlink_legacy_items:
                        derived_display = build_referring_domains_display(
                            raw_referring_domains=None,
                            raw_backlinks=backlink_legacy_items,
                            limit=backlinks_limit,
                            offset=backlinks_offset,
                        )
                        referring_domains_result = {
                            "total_count": derived_display["total_count"],
                            "items": derived_display["items"],
                        }
                except Exception as legacy_error:
                    logger.warning(
                        "Legacy backlink fallback failed for referring domains",
                        domain=domain,
                        error=str(legacy_error),
                    )
        else:
            referring_domains_result = empty_section()

        return {
            "success": True,
            "domain": domain,
            "detailed_data_available": report.detailed_data_available or {},
            "keywords": {
                "total_count": keywords_result["total_count"],
                "items": keywords_result["items"],
            },
            "referring_domains": {
                "total_count": referring_domains_result["total_count"],
                "items": referring_domains_result["items"],
            },
            "backlinks": {
                "total_count": backlinks_result["total_count"],
                "items": backlinks_result["items"],
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get report details", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get report details")


@router.get("/reports/{domain}/history", response_model=HistoricalData)
async def get_domain_history(domain: str, current_user = Depends(get_current_user)):
    """
    Get historical metrics for a domain (ranking, traffic)
    """
    try:
        from uuid import UUID
        service = AnalysisService()
        user_id = UUID(current_user['id']) if current_user and 'id' in current_user else None
        history = await service.get_or_fetch_historical_data(domain, user_id)

        if not history:
             raise HTTPException(status_code=404, detail="Historical data not available")

        return history
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get domain history", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get domain history")


@router.get("/reports", response_model=List[DomainAnalysisReport])
async def list_reports( 
    limit: int = Query(10, ge=1, le=100), 
    offset: int = Query(0, ge=0), 
    status: Optional[str] = Query(None),
    current_user = Depends(get_current_user)
):
    """
    List domain analysis reports with pagination, filtered by current user
    """
    try:
        db = get_database()
        user_id = _get_user_id(current_user)
        if not user_id:
            # If no user ID (unauthorized), return empty list or raise
            return []
        
        # Build query
        query = (await db._get_client()).table('reports').select( 
            'id, domain_name, status, analysis_timestamp, processing_time_seconds, error_message, analysis_phase, analysis_mode, data_for_seo_metrics, detailed_data_available, created_at, user_id' 
        ).eq('user_id', user_id)
        
        if status:
            query = query.eq('status', status)

        
        # Add pagination
        query = query.order('created_at', desc=True).range(offset, offset + limit - 1)
        
        try:
            result = await query.execute()
        except Exception as query_error:
            logger.error("Database query failed in list_reports", error=str(query_error))
            raise HTTPException(status_code=500, detail="Failed to query reports from database")
        
        reports = []
        for report_data in result.data:
            try:
                # Parse backlinks_page_summary if present
                backlinks_page_summary = None
                if report_data.get('backlinks_page_summary'):
                    try:
                        from models.domain_analysis import BulkPageSummaryResult
                        backlinks_page_summary = BulkPageSummaryResult(**report_data['backlinks_page_summary'])
                    except Exception as e:
                        logger.debug("Failed to parse backlinks_page_summary in list_reports", domain=report_data.get('domain_name'), error=str(e))
                
                # Parse analysis_timestamp
                analysis_timestamp = parse_iso_datetime(report_data.get('analysis_timestamp'))
                if not analysis_timestamp:
                    analysis_timestamp = datetime.utcnow()
                
                # Parse status - handle old reports that might have different status values
                from models.domain_analysis import AnalysisStatus
                status_value = report_data.get('status', 'pending')
                try:
                    status = AnalysisStatus(status_value)
                except (ValueError, TypeError):
                    logger.debug("Invalid status value, defaulting to pending", domain=report_data.get('domain_name'), status=status_value)
                    status = AnalysisStatus.PENDING
                
                # Parse analysis_phase - handle old reports
                from models.domain_analysis import AnalysisPhase
                analysis_phase = report_data.get('analysis_phase')
                if analysis_phase:
                    try:
                        analysis_phase = AnalysisPhase(analysis_phase)
                    except (ValueError, TypeError):
                        logger.debug("Invalid analysis_phase, using default", domain=report_data.get('domain_name'), phase=analysis_phase)
                        analysis_phase = AnalysisPhase.ESSENTIAL
                else:
                    analysis_phase = AnalysisPhase.ESSENTIAL
                
                # Parse analysis_mode - handle old reports
                from models.domain_analysis import AnalysisMode
                analysis_mode = report_data.get('analysis_mode')
                if analysis_mode:
                    try:
                        analysis_mode = AnalysisMode(analysis_mode)
                    except (ValueError, TypeError):
                        logger.debug("Invalid analysis_mode, using default", domain=report_data.get('domain_name'), mode=analysis_mode)
                        analysis_mode = AnalysisMode.LEGACY
                else:
                    analysis_mode = AnalysisMode.LEGACY
                
                report = DomainAnalysisReport(
                    domain_name=report_data['domain_name'],
                    user_id=report_data.get('user_id'),
                    analysis_timestamp=analysis_timestamp,
                    status=status,
                    data_for_seo_metrics=report_data.get('data_for_seo_metrics'),
                    wayback_machine_summary=report_data.get('wayback_machine_summary'),
                    llm_analysis=report_data.get('llm_analysis'),
                    raw_data_links=report_data.get('raw_data_links'),
                    detailed_data_available=report_data.get('detailed_data_available', {}),
                    analysis_phase=analysis_phase,
                    analysis_mode=analysis_mode,
                    processing_time_seconds=report_data.get('processing_time_seconds'),
                    error_message=report_data.get('error_message'),
                    backlinks_page_summary=backlinks_page_summary
                )
                reports.append(report)
            except Exception as e:
                logger.error("Failed to parse report in list", domain=report_data.get('domain_name'), error=str(e), error_type=type(e).__name__, report_keys=list(report_data.keys()) if isinstance(report_data, dict) else None, exc_info=True)
                # Skip this report but continue with others
                continue
        
        if not reports and result.data:
            # If we have data but no reports were parsed, log a warning
            logger.warning("No reports could be parsed from database results", total_records=len(result.data), first_domain=result.data[0].get('domain_name') if result.data else None)
        
        logger.info("Reports listed successfully", count=len(reports), limit=limit, offset=offset)
        
        return reports
        
    except Exception as e:
        logger.error("Failed to list reports", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list reports")


@router.get("/reports/{domain}/keywords")
async def get_domain_keywords( domain: str, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0), current_user = Depends(get_current_user) ):
    """
    Get detailed keywords data for a domain (on-demand from DataForSEO)
    """
    try:
        db, _ = await _get_owned_report_or_404(domain, current_user)
        
        from models.domain_analysis import DetailedDataType
        keyword_result = await db.get_detailed_items(domain, DetailedDataType.KEYWORDS, limit, offset)

        if not keyword_result["items"]:
            raise HTTPException(status_code=404, detail="Keywords data not available")

        return {
            "domain": domain,
            "total_count": keyword_result["total_count"],
            "limit": limit,
            "offset": offset,
            "keywords": shape_keyword_items(keyword_result["items"]),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get keywords", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get keywords")


@router.get("/reports/{domain}/keywords/export")
async def export_domain_keywords(domain: str, current_user = Depends(get_current_user)):
    """
    Get all keywords data for CSV export (no pagination)
    """
    try:
        db, _ = await _get_owned_report_or_404(domain, current_user)
        
        from models.domain_analysis import DetailedDataType
        keyword_result = await db.get_detailed_items(domain, DetailedDataType.KEYWORDS, 100000, 0)

        if not keyword_result["items"]:
            raise HTTPException(status_code=404, detail="Keywords data not available")

        keywords = shape_keyword_items(keyword_result["items"])

        return { "domain": domain, "total_count": keyword_result["total_count"], "keywords": keywords }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to export keywords", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to export keywords")


@router.get("/reports/{domain}/backlinks")
async def get_domain_backlinks( domain: str, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0), current_user = Depends(get_current_user) ):
    """
    Get detailed backlinks data for a domain (on-demand from DataForSEO)
    """
    try:
        db, _ = await _get_owned_report_or_404(domain, current_user)
        
        from models.domain_analysis import DetailedDataType
        backlink_result = await db.get_detailed_items(domain, DetailedDataType.BACKLINKS, limit, offset)

        if not backlink_result["items"]:
            raise HTTPException(status_code=404, detail="Backlinks data not available")

        return {
            "domain": domain,
            "total_count": backlink_result["total_count"],
            "limit": limit,
            "offset": offset,
            "backlinks": shape_backlink_items(backlink_result["items"]),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get backlinks", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get backlinks")


@router.get("/reports/{domain}/backlinks/export")
async def export_domain_backlinks(domain: str, current_user = Depends(get_current_user)):
    """
    Get all backlinks data for CSV export (no pagination)
    """
    try:
        db, _ = await _get_owned_report_or_404(domain, current_user)
        
        from models.domain_analysis import DetailedDataType
        backlink_result = await db.get_detailed_items(domain, DetailedDataType.BACKLINKS, 100000, 0)

        if not backlink_result["items"]:
            raise HTTPException(status_code=404, detail="Backlinks data not available")

        mapped_backlinks = shape_backlink_items(backlink_result["items"])

        return { "domain": domain, "total_count": backlink_result["total_count"], "backlinks": mapped_backlinks }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to export backlinks", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to export backlinks")


# ) Old delete endpoint removed - using comprehensive delete_domain_analysis method instead (see end of file


@router.post("/reports/{domain}/reanalyze")
async def reanalyze_domain_ai( domain: str, request: dict ):
    """
    Re-run AI analysis with additional detailed data
    """
    try:
        db = get_database()
        report = await db.get_report(domain)
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Get the requested data types
        include_backlinks = request.get("include_backlinks", False)
        include_keywords = request.get("include_keywords", False)
        include_referring_domains = request.get("include_referring_domains", False)
        
        # Get existing detailed data from database instead of making new API calls
        additional_data = {}
        
        from services.database import DetailedDataType
        
        if include_backlinks:
            backlinks_result = await db.get_detailed_items(domain, DetailedDataType.BACKLINKS, 100000, 0)
            if backlinks_result["items"]:
                additional_data["backlinks"] = shape_backlink_items(backlinks_result["items"])
        
        if include_keywords:
            keywords_result = await db.get_detailed_items(domain, DetailedDataType.KEYWORDS, 100000, 0)
            if keywords_result["items"]:
                additional_data["keywords"] = shape_keyword_items(keywords_result["items"])
        
        if include_referring_domains:
            referring_domains_result = await db.get_derived_referring_domains(domain, 100000, 0)
            if referring_domains_result["items"]:
                additional_data["referring_domains"] = shape_referring_domain_items(referring_domains_result["items"])
        
        # Get existing data in the format expected by enhanced LLM service
        existing_data = { "domain": domain, "essential_metrics": { "domain_rating": report.data_for_seo_metrics.domain_rating_dr if report.data_for_seo_metrics else 0,  # This is actually DataForSEO domain rank
                "organic_traffic": report.data_for_seo_metrics.organic_traffic_est if report.data_for_seo_metrics else 0, "total_keywords": report.data_for_seo_metrics.total_keywords if report.data_for_seo_metrics else 0 }, "detailed_data": { "backlinks": { "total_count": len(additional_data.get("backlinks", [])), "items": additional_data.get("backlinks", []) }, "keywords": { "total_count": len(additional_data.get("keywords", [])), "items": additional_data.get("keywords", []) }, "referring_domains": { "total_count": len(additional_data.get("referring_domains", [])), "items": additional_data.get("referring_domains", []) } }, "wayback_data": report.wayback_machine_summary.dict() if report.wayback_machine_summary else {} }
        
        # Use the combined data
        combined_data = existing_data
        
        # Generate new AI analysis
        from services.external_apis import LLMService
        llm_service = LLMService()
        
        logger.info("Re-analyzing with data", domain=domain, data_keys=list(combined_data.keys()), include_backlinks=include_backlinks, include_keywords=include_keywords)
        
        # Use enhanced LLM analysis directly - no fallback
        logger.info("Using enhanced LLM analysis for domain buyer insights", domain=domain)
        
        # Set a timeout for LLM service
        import asyncio
        try:
            llm_data = asyncio.wait_for( llm_service.generate_enhanced_analysis(domain, combined_data), timeout=120.0 ) # 2 minute timeout for enhanced analysis
        except asyncio.TimeoutError:
            logger.error("LLM service timed out during enhanced analysis", domain=domain)
            raise HTTPException(status_code=500, detail="LLM service timed out. Enhanced analysis requires more time.")
        except Exception as e:
            logger.error("LLM service failed during enhanced analysis", domain=domain, error=str(e))
            raise HTTPException(status_code=500, detail=f"LLM service failed: {str(e)}")
        
        if not llm_data:
            raise HTTPException(status_code=500, detail="Failed to generate AI analysis. Please check your LLM provider configuration in Supabase.")
        
        # Update the report with new AI analysis
        from models.domain_analysis import LLMAnalysis
        new_llm_analysis = LLMAnalysis(**llm_data)
        
        # Update report in database
        report.llm_analysis = new_llm_analysis
        await db.save_report(report)
        
        logger.info("AI analysis updated successfully", domain=domain, include_backlinks=include_backlinks, include_keywords=include_keywords)
        
        return { "success": True, "message": "AI analysis updated successfully", "llm_analysis": new_llm_analysis.dict() }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to reanalyze domain AI", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to reanalyze AI")


def _generate_fallback_analysis(domain: str, data: dict, include_backlinks: bool, include_keywords: bool) -> dict:
    """Generate meaningful fallback analysis based on collected data - focused on domain buyers"""
    
    # Extract data for analysis
    analytics = data.get("analytics", {})
    backlinks_summary = data.get("backlinks_summary", {})
    backlinks_items = data.get("backlinks", {}).get("items", [])
    keywords_items = data.get("keywords", {}).get("items", [])
    wayback = data.get("wayback", {})
    
    # Calculate metrics
    total_backlinks = backlinks_summary.get("backlinks", 0)
    total_referring_domains = backlinks_summary.get("referring_domains", 0)
    total_keywords = len(keywords_items)
    
    # Analyze backlinks if available
    backlink_analysis = []
    if backlinks_items:
        high_authority_count = sum(1 for b in backlinks_items if b.get("domain_from_rank", 0) >= 70)
        dofollow_count = sum(1 for b in backlinks_items if b.get("dofollow", False))
        backlink_analysis = [ f"Found {len(backlinks_items)} detailed backlinks", f"{high_authority_count} from high-authority domains (DR≥70)", f"{dofollow_count} dofollow links"
        ]
    
    # Analyze keywords if available
    keyword_analysis = []
    if keywords_items:
        top_keywords = [k.get("keyword", "") for k in keywords_items[:5]]
        keyword_analysis = [ f"Analyzed {total_keywords} keywords", f"Top keywords: {', '.join(top_keywords[:3])}"
        ]
    
    # Generate domain buyer-focused summary
    summary_parts = [f"Domain analysis for {domain} - Buyer Recommendation"]
    if include_backlinks and backlinks_items:
        summary_parts.append(f"with {len(backlinks_items)} detailed backlinks")
    if include_keywords and keywords_items:
        summary_parts.append(f"and {total_keywords} keywords")
    summary_parts.append("(LLM service unavailable - using data-driven analysis)")
    
    summary = " ".join(summary_parts)
    
    # Generate buy recommendation based on data with domain buyer focus
    buy_recommendation = "CAUTION"
    reasoning = ""
    risk_level = "medium"
    potential_value = "medium"
    
    if total_backlinks > 1000000 and total_referring_domains > 1000:
        buy_recommendation = "BUY"
        reasoning = f"Strong domain with {total_backlinks:,} backlinks and {total_referring_domains:,} referring domains. High SEO value potential."
        risk_level = "low"
        potential_value = "high"
    elif total_backlinks > 100000 and total_referring_domains > 100:
        buy_recommendation = "CAUTION"
        reasoning = f"Moderate domain with {total_backlinks:,} backlinks. Requires backlink quality audit before purchase."
        risk_level = "medium"
        potential_value = "medium"
    else:
        buy_recommendation = "NO-BUY"
        reasoning = f"Weak domain with only {total_backlinks:,} backlinks. Limited SEO value for domain buyers."
        risk_level = "high"
        potential_value = "low"
    
    # Generate valuable assets for domain buyers
    valuable_assets = []
    if total_backlinks > 0:
        valuable_assets.append(f"Strong backlink foundation with {total_backlinks:,} total backlinks")
    if total_referring_domains > 0:
        valuable_assets.append(f"Diverse link profile from {total_referring_domains:,} referring domains")
    if total_keywords > 0:
        valuable_assets.append(f"Established keyword presence with {total_keywords} tracked keywords")
    if not valuable_assets:
        valuable_assets.append("Domain data successfully collected for analysis")
    
    # Generate major concerns for domain buyers
    major_concerns = []
    if total_backlinks == 0:
        major_concerns.append("No backlinks detected - significant SEO disadvantage")
    if total_referring_domains < 10:
        major_concerns.append("Limited referring domain diversity - weak link profile")
    if total_keywords == 0:
        major_concerns.append("No keyword data available - unclear content direction")
    major_concerns.append("LLM service unavailable - advanced AI insights not available")
    
    # Generate content strategy for domain buyers
    content_strategy = { "primary_niche": "General content strategy", "secondary_niches": [], "first_articles": [], "target_keywords": [] }
    
    if keywords_items:
        # Extract common themes from keywords for content strategy
        keyword_themes = set()
        top_keywords = []
        for k in keywords_items[:10]:
            keyword = k.get("keyword", "").lower()
            top_keywords.append(k.get("keyword", ""))
            if "seo" in keyword:
                keyword_themes.add("SEO Tools & Services")
            elif "marketing" in keyword:
                keyword_themes.add("Digital Marketing")
            elif "data" in keyword:
                keyword_themes.add("Data Analytics")
        
        if keyword_themes:
            content_strategy["primary_niche"] = list(keyword_themes)[0]
            content_strategy["secondary_niches"] = list(keyword_themes)[1:3]
        else:
            content_strategy["primary_niche"] = "Content optimization based on keyword data"
        
        content_strategy["target_keywords"] = top_keywords[:5]
        content_strategy["first_articles"] = [ f"How to optimize for {top_keywords[0]}" if top_keywords else "Content strategy article", f"Complete guide to {top_keywords[1]}" if len(top_keywords) > 1 else "SEO optimization guide", f"Best practices for {top_keywords[2]}" if len(top_keywords) > 2 else "Digital marketing tips"
        ]
    else:
        content_strategy = { "primary_niche": "Content strategy development", "secondary_niches": ["SEO optimization", "Digital marketing"], "first_articles": [ "Content strategy for new website", "SEO optimization guide", "Digital marketing best practices"
            ], "target_keywords": ["content strategy", "SEO", "digital marketing"] }
    
    # Generate pros and cons for domain buyers
    pros_and_cons = []
    if include_backlinks and backlinks_items:
        pros_and_cons.append({ "type": "pro", "description": f"Strong backlink foundation with {len(backlinks_items)} analyzed backlinks", "impact": "high" if len(backlinks_items) > 100 else "medium", "example": f"Sample includes {high_authority_count} high-DR domains" })
        if high_authority_count < 5:
            pros_and_cons.append({ "type": "con", "description": "Limited high-authority backlinks", "impact": "medium", "example": f"Only {high_authority_count} domains with DR 70+" })
    
    if include_keywords and keywords_items:
        pros_and_cons.append({ "type": "pro", "description": f"Established keyword presence with {total_keywords} tracked keywords", "impact": "high" if total_keywords > 50 else "medium", "example": f"Top keywords: {', '.join([k.get('keyword', '') for k in keywords_items[:3]])}" })
    
    # Generate action plan for domain buyers
    action_plan = { "immediate_actions": [ "Set up website with proper SEO structure", "Create content calendar based on keyword analysis", "Set up Google Analytics and Search Console"
        ], "first_month": [ "Publish first 5 articles targeting identified keywords", "Begin outreach to high-DR referring domains", "Monitor backlink profile for any toxic links"
        ], "long_term_strategy": [ "Develop comprehensive content strategy", "Build relationships with referring domains", "Regular SEO monitoring and optimization"
        ] }
    
    return { "buy_recommendation": { "recommendation": buy_recommendation, "confidence": 0.7, "reasoning": reasoning, "risk_level": risk_level, "potential_value": potential_value }, "valuable_assets": valuable_assets, "major_concerns": major_concerns, "content_strategy": content_strategy, "action_plan": action_plan, "pros_and_cons": pros_and_cons, "summary": f"Domain analysis for {domain} - {buy_recommendation} recommendation based on {total_backlinks} backlinks and {total_keywords} keywords", "confidence_score": 0.7 }


@router.get("/reports/{domain}/pdf")
async def export_report_pdf(domain: str):
    """
    Export domain analysis report as PDF
    """
    try:
        db = get_database()
        report = await db.get_report(domain)
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Convert report to dictionary for PDF generation
        report_data = { "domain": domain, "data_for_seo_metrics": report.data_for_seo_metrics.dict() if report.data_for_seo_metrics else {}, "wayback_machine_summary": report.wayback_machine_summary.dict() if report.wayback_machine_summary else {}, "llm_analysis": report.llm_analysis.dict() if report.llm_analysis else {} }
        
        # Generate PDF
        pdf_service = PDFService()
        pdf_bytes = pdf_service.generate_domain_analysis_pdf(domain, report_data)
        
        # Create streaming response
        pdf_stream = io.BytesIO(pdf_bytes)
        
        return StreamingResponse( io.BytesIO(pdf_bytes), media_type="application/pdf", headers={ "Content-Disposition": f"attachment; filename=domain_analysis_{domain}.pdf" } )
        
    except Exception as e:
        logger.error("Failed to export PDF", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate PDF report")


@router.delete("/reports/{domain}")
async def delete_report(domain: str, current_user = Depends(get_current_user)):
    """
    Delete a domain analysis and all related records
    This will remove:
    - Main report record
    - Detailed analysis data (backlinks, keywords, referring domains)
    - Raw data cache
    - Async tasks
    - Mode configuration
    """
    try:
        db = get_database()
        
        # Check if report exists
        report = await db.get_report(domain)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
            
        # Ownership check
        if report.user_id and str(report.user_id) != str(getattr(current_user, 'id', None)):
            raise HTTPException(status_code=403, detail="You do not have permission to delete this report")
        
        # Delete all related records
        logger.info("Calling delete_domain_analysis method", domain=domain)
        success = await db.delete_domain_analysis(domain)
        logger.info("delete_domain_analysis method completed", domain=domain, success=success)
        
        if success:
            logger.info("Report deleted successfully", domain=domain)
            return { "success": True, "message": "Report deleted successfully" }
        else:
            logger.warning("No records found to delete", domain=domain)
            return { "success": True, "message": "No records found to delete" }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete report", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete report")
