"""
Reports API routes
"""

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime
import structlog
import io

from models.domain_analysis import ReportResponse, DomainAnalysisReport
from services.database import get_database, DataSource
from services.external_apis import DataForSEOService
from services.pdf_service import PDFService

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
            # Include error message if report failed
            if report.status == "failed" and report.error_message:
                return ReportResponse(
                    success=False,
                    message=f"Analysis failed: {report.error_message}",
                    report=report  # Include report so frontend can access error_message
                )
            return ReportResponse(
                success=False,
                message=f"Report not ready. Status: {report.status}",
                report=report  # Include report even if not completed so frontend can check status
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


@router.get("/reports/{domain}/page-summary")
async def get_page_summary(domain: str):
    """
    Get page summary data (backlinks summary) from raw_data_cache for a domain
    This data is collected during individual domain analysis
    """
    try:
        db = get_database()
        
        # Get cached DataForSEO data which contains backlinks_summary
        raw_data = await db.get_raw_data(domain, DataSource.DATAFORSEO)
        
        if not raw_data:
            raise HTTPException(status_code=404, detail="Page summary data not found for this domain")
        
        # Extract backlinks_summary from cached data
        backlinks_summary = raw_data.get("backlinks_summary")
        
        if not backlinks_summary:
            raise HTTPException(status_code=404, detail="Backlinks summary not found in cached data")
        
        logger.info("Page summary retrieved successfully", domain=domain)
        
        return {
            "success": True,
            "data": backlinks_summary,
            "message": "Page summary retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get page summary", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get page summary")


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
        
        # Build query - only select necessary fields to improve performance
        # Note: We still need '*' to get all JSONB fields, but we can optimize later if needed
        query = db.client.table('reports').select('*')
        
        if status:
            query = query.eq('status', status)
        
        # Add pagination
        query = query.order('created_at', desc=True).range(offset, offset + limit - 1)
        
        try:
            result = query.execute()
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
                        logger.debug("Failed to parse backlinks_page_summary in list_reports", 
                                   domain=report_data.get('domain_name'), error=str(e))
                
                # Parse analysis_timestamp
                analysis_timestamp = report_data.get('analysis_timestamp')
                if isinstance(analysis_timestamp, str):
                    try:
                        analysis_timestamp = datetime.fromisoformat(analysis_timestamp.replace('Z', '+00:00'))
                    except Exception as e:
                        logger.debug("Failed to parse analysis_timestamp", 
                                   domain=report_data.get('domain_name'), 
                                   timestamp=analysis_timestamp, 
                                   error=str(e))
                        analysis_timestamp = datetime.utcnow()
                elif not analysis_timestamp:
                    analysis_timestamp = datetime.utcnow()
                
                # Parse status - handle old reports that might have different status values
                from models.domain_analysis import AnalysisStatus
                status_value = report_data.get('status', 'pending')
                try:
                    status = AnalysisStatus(status_value)
                except (ValueError, TypeError):
                    logger.debug("Invalid status value, defaulting to pending", 
                               domain=report_data.get('domain_name'), 
                               status=status_value)
                    status = AnalysisStatus.PENDING
                
                # Parse analysis_phase - handle old reports
                from models.domain_analysis import AnalysisPhase
                analysis_phase = report_data.get('analysis_phase')
                if analysis_phase:
                    try:
                        analysis_phase = AnalysisPhase(analysis_phase)
                    except (ValueError, TypeError):
                        logger.debug("Invalid analysis_phase, using default", 
                                   domain=report_data.get('domain_name'), 
                                   phase=analysis_phase)
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
                        logger.debug("Invalid analysis_mode, using default", 
                                   domain=report_data.get('domain_name'), 
                                   mode=analysis_mode)
                        analysis_mode = AnalysisMode.LEGACY
                else:
                    analysis_mode = AnalysisMode.LEGACY
                
                report = DomainAnalysisReport(
                    domain_name=report_data['domain_name'],
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
                logger.error("Failed to parse report in list", 
                           domain=report_data.get('domain_name'), 
                           error=str(e),
                           error_type=type(e).__name__,
                           report_keys=list(report_data.keys()) if isinstance(report_data, dict) else None,
                           exc_info=True)
                # Skip this report but continue with others
                continue
        
        if not reports and result.data:
            # If we have data but no reports were parsed, log a warning
            logger.warning("No reports could be parsed from database results", 
                         total_records=len(result.data),
                         first_domain=result.data[0].get('domain_name') if result.data else None)
        
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
    Get detailed keywords data for a domain (on-demand from DataForSEO)
    """
    try:
        db = get_database()
        report = await db.get_report(domain)
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Get detailed keywords data from database
        from models.domain_analysis import DetailedDataType
        detailed_data = await db.get_detailed_data(domain, DetailedDataType.KEYWORDS)
        
        if not detailed_data:
            raise HTTPException(status_code=404, detail="Keywords data not available")
        
        # Extract keywords from the saved data
        keywords = detailed_data.json_data.get("items", [])
        
        # Validate that we actually have keywords
        if not keywords or len(keywords) == 0:
            raise HTTPException(status_code=404, detail="No keywords data available for this domain")
        
        # Filter out sample/test keywords
        domain_lower = domain.lower().replace('www.', '')
        valid_keywords = []
        
        for keyword in keywords:
            serp_item = keyword.get("ranked_serp_element", {}).get("serp_item", {})
            url = serp_item.get("url", "")
            keyword_text = keyword.get("keyword_data", {}).get("keyword", "")
            
            # Skip if URL is empty
            if not url:
                continue
            
            url_lower = url.lower()
            
            # Filter out sample/test data from DataForSEO
            if any(test_domain in url_lower for test_domain in [
                'dataforseo.com',
                'example.com',
                'test.com',
                'sample.com',
                'demo.com'
            ]):
                logger.debug("Filtered out sample keyword", domain=domain, keyword=keyword_text, url=url)
                continue
            
            valid_keywords.append(keyword)
        
        # If no valid keywords after filtering, return 404
        if not valid_keywords:
            logger.warning("No valid keywords after filtering sample data", domain=domain, original_count=len(keywords))
            raise HTTPException(status_code=404, detail="No valid keywords data available for this domain (sample data filtered out)")
        
        # Use actual count of valid keywords
        total_count = len(valid_keywords)
        
        # Apply pagination to valid keywords
        paginated_keywords = valid_keywords[offset:offset + limit]
        
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


@router.get("/reports/{domain}/keywords/export")
async def export_domain_keywords(domain: str):
    """
    Get all keywords data for CSV export (no pagination)
    """
    try:
        db = get_database()
        report = await db.get_report(domain)
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Get detailed keywords data from database
        from models.domain_analysis import DetailedDataType
        detailed_data = await db.get_detailed_data(domain, DetailedDataType.KEYWORDS)
        
        if not detailed_data:
            raise HTTPException(status_code=404, detail="Keywords data not available")
        
        # Extract all keywords from the saved data
        keywords = detailed_data.json_data.get("items", [])
        
        return {
            "domain": domain,
            "total_count": len(keywords),
            "keywords": keywords
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to export keywords", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to export keywords")


@router.get("/reports/{domain}/backlinks")
async def get_domain_backlinks(
    domain: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Get detailed backlinks data for a domain (on-demand from DataForSEO)
    """
    try:
        db = get_database()
        report = await db.get_report(domain)
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Get detailed backlinks data from database
        from models.domain_analysis import DetailedDataType
        detailed_data = await db.get_detailed_data(domain, DetailedDataType.BACKLINKS)
        
        if not detailed_data:
            raise HTTPException(status_code=404, detail="Backlinks data not available")
        
        # Extract backlinks from the saved data
        raw_backlinks = detailed_data.json_data.get("items", [])
        # Use the actual count from the detailed data, not the summary metrics
        total_count = len(raw_backlinks)
        
        # Map DataForSEO response to frontend interface
        mapped_backlinks = []
        for item in raw_backlinks:
            mapped_backlinks.append({
                "domain": item.get("domain_from", ""),
                "domain_rank": item.get("domain_from_rank", 0),
                "anchor_text": item.get("anchor", ""),
                "backlinks_count": item.get("links_count", 0),
                "first_seen": item.get("first_seen", ""),
                "last_seen": item.get("last_seen", "")
            })
        
        # Apply pagination
        paginated_backlinks = mapped_backlinks[offset:offset + limit]
        
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


@router.get("/reports/{domain}/backlinks/export")
async def export_domain_backlinks(domain: str):
    """
    Get all backlinks data for CSV export (no pagination)
    """
    try:
        db = get_database()
        report = await db.get_report(domain)
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Get detailed backlinks data from database
        from models.domain_analysis import DetailedDataType
        detailed_data = await db.get_detailed_data(domain, DetailedDataType.BACKLINKS)
        
        if not detailed_data:
            raise HTTPException(status_code=404, detail="Backlinks data not available")
        
        # Extract all backlinks from the saved data
        raw_backlinks = detailed_data.json_data.get("items", [])
        
        # Map DataForSEO response to frontend interface with comprehensive data
        mapped_backlinks = []
        for item in raw_backlinks:
            mapped_backlinks.append({
                "domain": item.get("domain_from", ""),
                "domain_rank": item.get("domain_from_rank", 0),
                "anchor_text": item.get("anchor", ""),
                "backlinks_count": item.get("links_count", 0),
                "first_seen": item.get("first_seen", ""),
                "last_seen": item.get("last_seen", ""),
                # Additional comprehensive fields from DataForSEO
                "url_from": item.get("url_from", ""),
                "url_to": item.get("url_to", ""),
                "link_type": item.get("type", ""),
                "link_attributes": item.get("attributes", ""),
                "page_from_title": item.get("page_from_title", ""),
                "page_from_rank": item.get("page_from_rank", 0),
                "page_from_internal_links_count": item.get("page_from_internal_links", 0),
                "page_from_external_links_count": item.get("page_from_external_links", 0),
                "page_from_rank_absolute": item.get("rank", 0),
                # Additional useful fields
                "dofollow": item.get("dofollow", False),
                "is_new": item.get("is_new", False),
                "is_lost": item.get("is_lost", False),
                "is_broken": item.get("is_broken", False),
                "url_from_https": item.get("url_from_https", False),
                "url_to_https": item.get("url_to_https", False),
                "page_from_status_code": item.get("page_from_status_code", 0),
                "url_to_status_code": item.get("url_to_status_code", 0),
                "backlink_spam_score": item.get("backlink_spam_score", 0),
                "url_to_spam_score": item.get("url_to_spam_score", 0),
                "page_from_size": item.get("page_from_size", 0),
                "page_from_encoding": item.get("page_from_encoding", ""),
                "page_from_language": item.get("page_from_language", ""),
                "domain_from_ip": item.get("domain_from_ip", ""),
                "domain_from_country": item.get("domain_from_country", ""),
                "domain_from_platform_type": item.get("domain_from_platform_type", []),
                "semantic_location": item.get("semantic_location", ""),
                "alt": item.get("alt", ""),
                "image_url": item.get("image_url", ""),
                "text_pre": item.get("text_pre", ""),
                "text_post": item.get("text_post", ""),
                "tld_from": item.get("tld_from", ""),
                "domain_to": item.get("domain_to", ""),
                "is_indirect_link": item.get("is_indirect_link", False),
                "indirect_link_path": item.get("indirect_link_path", ""),
                "url_to_redirect_target": item.get("url_to_redirect_target", ""),
                "prev_seen": item.get("prev_seen", ""),
                "group_count": item.get("group_count", 0),
                "original": item.get("original", False),
                "item_type": item.get("item_type", ""),
                "domain_from_is_ip": item.get("domain_from_is_ip", False)
            })
        
        return {
            "domain": domain,
            "total_count": len(mapped_backlinks),
            "backlinks": mapped_backlinks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to export backlinks", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to export backlinks")


# Old delete endpoint removed - using comprehensive delete_domain_analysis method instead (see end of file)


@router.post("/reports/{domain}/reanalyze")
async def reanalyze_domain_ai(
    domain: str,
    request: dict
):
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
            backlinks_data = await db.get_detailed_data(domain, DetailedDataType.BACKLINKS)
            if backlinks_data:
                additional_data["backlinks"] = backlinks_data.json_data.get("items", [])
        
        if include_keywords:
            keywords_data = await db.get_detailed_data(domain, DetailedDataType.KEYWORDS)
            if keywords_data:
                additional_data["keywords"] = keywords_data.json_data.get("items", [])
        
        if include_referring_domains:
            referring_domains_data = await db.get_detailed_data(domain, DetailedDataType.REFERRING_DOMAINS)
            if referring_domains_data:
                additional_data["referring_domains"] = referring_domains_data.json_data.get("items", [])
        
        # Get existing data in the format expected by enhanced LLM service
        existing_data = {
            "domain": domain,
            "essential_metrics": {
                "domain_rating": report.data_for_seo_metrics.domain_rating_dr if report.data_for_seo_metrics else 0,  # This is actually DataForSEO domain rank
                "organic_traffic": report.data_for_seo_metrics.organic_traffic_est if report.data_for_seo_metrics else 0,
                "total_keywords": report.data_for_seo_metrics.total_keywords if report.data_for_seo_metrics else 0
            },
            "detailed_data": {
                "backlinks": {
                    "total_count": len(additional_data.get("backlinks", [])),
                    "items": additional_data.get("backlinks", [])
                },
                "keywords": {
                    "total_count": len(additional_data.get("keywords", [])),
                    "items": additional_data.get("keywords", [])
                },
                "referring_domains": {
                    "total_count": len(additional_data.get("referring_domains", [])),
                    "items": additional_data.get("referring_domains", [])
                }
            },
            "wayback_data": report.wayback_machine_summary.dict() if report.wayback_machine_summary else {}
        }
        
        # Use the combined data
        combined_data = existing_data
        
        # Generate new AI analysis
        from services.external_apis import LLMService
        llm_service = LLMService()
        
        logger.info("Re-analyzing with data", domain=domain, 
                   data_keys=list(combined_data.keys()),
                   include_backlinks=include_backlinks,
                   include_keywords=include_keywords)
        
        # Use enhanced LLM analysis directly - no fallback
        logger.info("Using enhanced LLM analysis for domain buyer insights", domain=domain)
        
        # Set a timeout for LLM service
        import asyncio
        try:
            llm_data = await asyncio.wait_for(
                llm_service.generate_enhanced_analysis(domain, combined_data),
                timeout=120.0  # 2 minute timeout for enhanced analysis
            )
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
        
        logger.info("AI analysis updated successfully", domain=domain, 
                   include_backlinks=include_backlinks, include_keywords=include_keywords)
        
        return {
            "success": True, 
            "message": "AI analysis updated successfully",
            "llm_analysis": new_llm_analysis.dict()
        }
        
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
        backlink_analysis = [
            f"Found {len(backlinks_items)} detailed backlinks",
            f"{high_authority_count} from high-authority domains (DR≥70)",
            f"{dofollow_count} dofollow links"
        ]
    
    # Analyze keywords if available
    keyword_analysis = []
    if keywords_items:
        top_keywords = [k.get("keyword", "") for k in keywords_items[:5]]
        keyword_analysis = [
            f"Analyzed {total_keywords} keywords",
            f"Top keywords: {', '.join(top_keywords[:3])}"
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
    content_strategy = {
        "primary_niche": "General content strategy",
        "secondary_niches": [],
        "first_articles": [],
        "target_keywords": []
    }
    
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
        content_strategy["first_articles"] = [
            f"How to optimize for {top_keywords[0]}" if top_keywords else "Content strategy article",
            f"Complete guide to {top_keywords[1]}" if len(top_keywords) > 1 else "SEO optimization guide",
            f"Best practices for {top_keywords[2]}" if len(top_keywords) > 2 else "Digital marketing tips"
        ]
    else:
        content_strategy = {
            "primary_niche": "Content strategy development",
            "secondary_niches": ["SEO optimization", "Digital marketing"],
            "first_articles": [
                "Content strategy for new website",
                "SEO optimization guide",
                "Digital marketing best practices"
            ],
            "target_keywords": ["content strategy", "SEO", "digital marketing"]
        }
    
    # Generate pros and cons for domain buyers
    pros_and_cons = []
    if include_backlinks and backlinks_items:
        pros_and_cons.append({
            "type": "pro",
            "description": f"Strong backlink foundation with {len(backlinks_items)} analyzed backlinks",
            "impact": "high" if len(backlinks_items) > 100 else "medium",
            "example": f"Sample includes {high_authority_count} high-DR domains"
        })
        if high_authority_count < 5:
            pros_and_cons.append({
                "type": "con",
                "description": "Limited high-authority backlinks",
                "impact": "medium",
                "example": f"Only {high_authority_count} domains with DR 70+"
            })
    
    if include_keywords and keywords_items:
        pros_and_cons.append({
            "type": "pro",
            "description": f"Established keyword presence with {total_keywords} tracked keywords",
            "impact": "high" if total_keywords > 50 else "medium",
            "example": f"Top keywords: {', '.join([k.get('keyword', '') for k in keywords_items[:3]])}"
        })
    
    # Generate action plan for domain buyers
    action_plan = {
        "immediate_actions": [
            "Set up website with proper SEO structure",
            "Create content calendar based on keyword analysis",
            "Set up Google Analytics and Search Console"
        ],
        "first_month": [
            "Publish first 5 articles targeting identified keywords",
            "Begin outreach to high-DR referring domains",
            "Monitor backlink profile for any toxic links"
        ],
        "long_term_strategy": [
            "Develop comprehensive content strategy",
            "Build relationships with referring domains",
            "Regular SEO monitoring and optimization"
        ]
    }
    
    return {
        "buy_recommendation": {
            "recommendation": buy_recommendation,
            "confidence": 0.7,
            "reasoning": reasoning,
            "risk_level": risk_level,
            "potential_value": potential_value
        },
        "valuable_assets": valuable_assets,
        "major_concerns": major_concerns,
        "content_strategy": content_strategy,
        "action_plan": action_plan,
        "pros_and_cons": pros_and_cons,
        "summary": f"Domain analysis for {domain} - {buy_recommendation} recommendation based on {total_backlinks} backlinks and {total_keywords} keywords",
        "confidence_score": 0.7
    }


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
        report_data = {
            "domain": domain,
            "data_for_seo_metrics": report.data_for_seo_metrics.dict() if report.data_for_seo_metrics else {},
            "wayback_machine_summary": report.wayback_machine_summary.dict() if report.wayback_machine_summary else {},
            "llm_analysis": report.llm_analysis.dict() if report.llm_analysis else {}
        }
        
        # Generate PDF
        pdf_service = PDFService()
        pdf_bytes = pdf_service.generate_domain_analysis_pdf(domain, report_data)
        
        # Create streaming response
        pdf_stream = io.BytesIO(pdf_bytes)
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=domain_analysis_{domain}.pdf"
            }
        )
        
    except Exception as e:
        logger.error("Failed to export PDF", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate PDF report")


@router.delete("/reports/{domain}")
async def delete_report(domain: str):
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
        
        # Delete all related records
        logger.info("Calling delete_domain_analysis method", domain=domain)
        success = await db.delete_domain_analysis(domain)
        logger.info("delete_domain_analysis method completed", domain=domain, success=success)
        
        if success:
            logger.info("Report deleted successfully", domain=domain)
            return {
                "success": True,
                "message": "Report deleted successfully"
            }
        else:
            logger.warning("No records found to delete", domain=domain)
            return {
                "success": True,
                "message": "No records found to delete"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete report", domain=domain, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete report")
