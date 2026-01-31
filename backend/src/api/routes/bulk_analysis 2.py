"""
Bulk Domain Analysis API routes
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Body
from typing import Optional, List, Dict, Any
import structlog
import uuid
from datetime import datetime, timedelta

from services.bulk_analysis_service import BulkAnalysisService
from services.namecheap_service import NamecheapService
from services.domain_scoring_service import DomainScoringService
from services.auto_trigger_service import AutoTriggerService
from services.database import get_database
from models.domain_analysis import (
    BulkDomainAnalysis, 
    NamecheapDomain,
    NamecheapDomainListResponse,
    NamecheapDomainSelection,
    NamecheapAnalysisResponse,
    ScoredDomain
)

logger = structlog.get_logger()
router = APIRouter()

# In-memory storage for CSV files (keyed by file_id)
# In production, consider using Redis or a proper cache
_csv_cache: Dict[str, Dict[str, Any]] = {}

# In-memory storage for scored domains (keyed by file_id)
_csv_scored_cache: Dict[str, Dict[str, Any]] = {}


@router.get("/domains")
async def get_bulk_domains(
    sort_by: str = Query("created_at", description="Field to sort by (created_at, domain_name, updated_at)"),
    order: str = Query("desc", description="Sort order (asc, desc)")
):
    """
    Get all bulk domain analysis records with optional sorting
    """
    try:
        db = get_database()
        records = await db.get_all_bulk_domains(sort_by=sort_by, order=order)
        
        # Convert to dict format for JSON response
        result = []
        for record in records:
            record_dict = {
                "id": record.id,
                "domain_name": record.domain_name,
                "provider": record.provider,
                "backlinks_bulk_page_summary": record.backlinks_bulk_page_summary.dict() if record.backlinks_bulk_page_summary else None,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None
            }
            result.append(record_dict)
        
        return {
            "success": True,
            "count": len(result),
            "domains": result
        }
        
    except Exception as e:
        logger.error("Failed to get bulk domains", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve domains: {str(e)}")


# Namecheap-specific routes

@router.post("/namecheap/upload-csv")
async def upload_namecheap_csv(
    file: UploadFile = File(...),
    load_to_db: bool = Query(False, description="Whether to load data into database (default: False, just parse and cache)")
):
    """
    Upload Namecheap CSV file and optionally load into namecheap_domains table
    
    If load_to_db=False (default), the file is parsed and cached in memory for viewing.
    If load_to_db=True, the table will be truncated before loading new data.
    Expected CSV format with header row containing all Namecheap fields.
    """
    try:
        # Read file content
        content = await file.read()
        file_content = content.decode('utf-8')
        
        logger.info("Received Namecheap CSV upload", filename=file.filename, size=len(file_content), load_to_db=load_to_db)
        
        # Parse CSV
        namecheap_service = NamecheapService()
        domains = namecheap_service.parse_csv_file(file_content)
        
        if not domains:
            raise HTTPException(status_code=400, detail="No valid domains found in CSV")
        
        if load_to_db:
            # Load into database
            result = await namecheap_service.load_namecheap_csv(file_content)
            
            if not result.get("success"):
                raise HTTPException(status_code=400, detail=result.get("message", "Failed to process CSV"))
            
            return {
                "success": True,
                "message": result.get("message"),
                "loaded_count": result.get("loaded_count", 0),
                "skipped_count": result.get("skipped_count", 0),
                "total_count": result.get("total_count", 0),
                "file_id": None  # Not needed for DB load
            }
        else:
            # Store in memory cache for viewing
            file_id = str(uuid.uuid4())
            _csv_cache[file_id] = {
                "domains": domains,
                "filename": file.filename,
                "uploaded_at": datetime.now(),
                "total_count": len(domains)
            }
            
            # Score domains automatically (with error handling)
            logger.info("Starting domain scoring", file_id=file_id, domain_count=len(domains))
            passed_domains = []
            failed_domains = []
            scoring_error = None
            
            try:
                scoring_service = DomainScoringService()
                scored_domains = scoring_service.score_domains(domains)
                
                # Verify scoring completed successfully
                if not scored_domains or len(scored_domains) == 0:
                    raise ValueError("Scoring service returned empty results")
                
                if len(scored_domains) != len(domains):
                    logger.warning("Scoring returned different count than input", 
                                 input_count=len(domains), 
                                 scored_count=len(scored_domains))
                
                # Separate passed and failed
                passed_domains = [s for s in scored_domains if s.filter_status == 'PASS']
                failed_domains = [s for s in scored_domains if s.filter_status == 'FAIL']
                
                # Get top 3000 domain names (for auto-trigger logic)
                top_3000_domains = [s.domain.name for s in scored_domains[:3000]]
                
                # Store scored domains in cache
                _csv_scored_cache[file_id] = {
                    "scored_domains": scored_domains,
                    "ranked_domains": passed_domains,  # Only PASS domains, sorted by score DESC
                    "top_3000_domains": top_3000_domains,
                    "scored_at": datetime.now(),
                    "passed_count": len(passed_domains),
                    "failed_count": len(failed_domains)
                }
                
                logger.info("Domain scoring completed successfully", 
                           total=len(scored_domains),
                           passed=len(passed_domains),
                           failed=len(failed_domains))
            except Exception as e:
                scoring_error = str(e)
                logger.error("Failed to score domains", error=scoring_error, exc_info=True)
                # Continue without scoring - domains will still be available for viewing
                # Store empty scoring cache to indicate scoring failed
                _csv_scored_cache[file_id] = {
                    "scored_domains": [],
                    "ranked_domains": [],
                    "top_3000_domains": [],
                    "scored_at": datetime.now(),
                    "passed_count": 0,
                    "failed_count": 0,
                    "scoring_error": scoring_error
                }
            
            # Clean up old cache entries (older than 1 hour)
            cutoff_time = datetime.now() - timedelta(hours=1)
            keys_to_remove = [
                k for k, v in _csv_cache.items() 
                if v.get("uploaded_at", datetime.min) < cutoff_time
            ]
            for k in keys_to_remove:
                del _csv_cache[k]
                if k in _csv_scored_cache:
                    del _csv_scored_cache[k]
            
            logger.info("CSV cached and scored", 
                       file_id=file_id, 
                       domain_count=len(domains),
                       passed=len(passed_domains),
                       failed=len(failed_domains))
            
            # Build response message
            if scoring_error:
                message = f"Parsed {len(domains)} domains. Scoring failed: {scoring_error}"
            else:
                message = f"Parsed {len(domains)} domains. {len(passed_domains)} passed filtering, {len(failed_domains)} failed."
            
            response_data = {
                "success": True,
                "message": message,
                "loaded_count": len(domains),
                "skipped_count": 0,
                "total_count": len(domains),
                "file_id": file_id,
            }
            
            # Only include scoring stats if scoring succeeded
            if not scoring_error and (len(passed_domains) > 0 or len(failed_domains) > 0):
                response_data["scoring_stats"] = {
                    "passed": len(passed_domains),
                    "failed": len(failed_domains),
                    "top_score": passed_domains[0].total_meaning_score if passed_domains else None
                }
            elif scoring_error:
                response_data["scoring_error"] = scoring_error
            
            return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to upload Namecheap CSV", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to process CSV: {str(e)}")


@router.get("/namecheap/csv-domains")
async def get_csv_domains(
    file_id: str = Query(..., description="File ID returned from upload"),
    sort_by: str = Query("name", description="Field to sort by"),
    order: str = Query("asc", description="Sort order (asc, desc)"),
    search: Optional[str] = Query(None, description="Search filter for domain name"),
    extensions: Optional[str] = Query(None, description="Comma-separated list of extensions to filter"),
    no_special_chars: Optional[bool] = Query(None, description="Filter domains with no special characters"),
    no_numbers: Optional[bool] = Query(None, description="Filter domains with no numbers"),
    filter_status: Optional[str] = Query(None, description="Filter by status: PASS, FAIL, or ALL"),
    limit: int = Query(100, description="Maximum number of records to return", ge=1, le=1000),
    offset: int = Query(0, description="Number of records to skip", ge=0)
):
    """
    Get paginated domains from cached CSV file (without database storage)
    """
    try:
        if file_id not in _csv_cache:
            raise HTTPException(status_code=404, detail="File not found or expired. Please upload again.")
        
        cache_entry = _csv_cache[file_id]
        all_domains = cache_entry.get("domains", [])
        
        if not all_domains:
            logger.warning("No domains found in cache", file_id=file_id)
            return NamecheapDomainListResponse(
                success=True,
                count=0,
                domains=[],
                total_count=0,
                has_more=False
            )
        
        # Helper function to normalize domain names for consistent matching
        def normalize_domain_name(name: str) -> str:
            """Normalize domain name for consistent matching"""
            if not name:
                return ""
            # Convert to lowercase and strip whitespace
            normalized = name.lower().strip()
            # Remove protocol if present
            normalized = normalized.replace('http://', '').replace('https://', '')
            # Remove www. prefix
            if normalized.startswith('www.'):
                normalized = normalized[4:]
            return normalized
        
        # Get scored domains if available
        scored_cache = _csv_scored_cache.get(file_id, {})
        scored_domains_map = {}  # Map normalized domain name -> ScoredDomain
        ranked_domains_list = []
        ranked_scored_map = {}  # Map normalized domain name -> ScoredDomain for ranked domains
        ranked_scored_domains = []  # Store ScoredDomain objects for PASS filter
        
        # Check if we should use ranked domains (when sorting by score/rank OR filtering by PASS)
        # Also use ranked domains if filter_status is PASS (only show passed domains)
        use_ranked_domains = (sort_by in ['total_meaning_score', 'rank'] or filter_status == 'PASS') and scored_cache
        
        if scored_cache:
            try:
                # Build scored_domains_map for attaching scores to domains
                scored_domains_list = scored_cache.get("scored_domains", [])
                logger.info("Building scored domains map", total_scored=len(scored_domains_list))
                
                for scored in scored_domains_list:
                    try:
                        domain_name = None
                        # Handle both ScoredDomain objects and dicts
                        if isinstance(scored, dict):
                            # Try multiple ways to get domain name from dict
                            if 'domain' in scored:
                                domain_obj = scored['domain']
                                if isinstance(domain_obj, dict):
                                    domain_name = domain_obj.get('name')
                                elif hasattr(domain_obj, 'name'):
                                    domain_name = domain_obj.name
                            if not domain_name:
                                domain_name = scored.get('domain_name')
                            
                            if domain_name:
                                # Normalize domain name for consistent matching
                                normalized_name = normalize_domain_name(domain_name)
                                scored_domains_map[normalized_name] = scored
                        else:
                            # ScoredDomain object
                            if hasattr(scored, 'domain'):
                                domain = scored.domain
                                # Try multiple ways to get name
                                if hasattr(domain, 'name'):
                                    domain_name = domain.name
                                elif isinstance(domain, dict):
                                    domain_name = domain.get('name')
                                
                                if domain_name:
                                    # Normalize domain name for consistent matching
                                    normalized_name = normalize_domain_name(domain_name)
                                    scored_domains_map[normalized_name] = scored
                    except Exception as e:
                        logger.warning("Failed to process individual scored domain", error=str(e), exc_info=True)
                        continue
                
                logger.info("Built scored domains map", map_size=len(scored_domains_map), sample_keys=list(scored_domains_map.keys())[:5])
                
                # Get ranked domains if sorting by score or filtering by PASS (keep as ScoredDomain objects for score attachment)
                if use_ranked_domains:
                    ranked_scored_domains = scored_cache.get("ranked_domains", [])
                    logger.info("Processing ranked domains", 
                               count=len(ranked_scored_domains),
                               filter_status=filter_status,
                               sort_by=sort_by)
                    
                    # Build map from ranked domains for score attachment
                    for scored in ranked_scored_domains:
                        try:
                            domain_name = None
                            if isinstance(scored, dict):
                                domain_obj = scored.get('domain', {})
                                if isinstance(domain_obj, dict):
                                    domain_name = domain_obj.get('name')
                                elif hasattr(domain_obj, 'name'):
                                    domain_name = domain_obj.name
                                if not domain_name:
                                    domain_name = scored.get('domain_name')
                            else:
                                # ScoredDomain object
                                if hasattr(scored, 'domain'):
                                    domain = scored.domain
                                    if hasattr(domain, 'name'):
                                        domain_name = domain.name
                                    elif isinstance(domain, dict):
                                        domain_name = domain.get('name')
                            
                            if domain_name:
                                # Normalize domain name for consistent matching
                                normalized_name = normalize_domain_name(domain_name)
                                ranked_scored_map[normalized_name] = scored
                                # Also add to main map if not already there
                                if normalized_name not in scored_domains_map:
                                    scored_domains_map[normalized_name] = scored
                        except Exception as e:
                            logger.warning("Failed to add ranked domain to map", error=str(e), exc_info=True)
                    
                    # Build ranked_domains_list for reference (used when not filtering by PASS)
                    # When filtering by PASS, we'll rebuild this list directly from ranked_scored_domains
                    if ranked_scored_domains:
                        try:
                            ranked_domains_list = []
                            for scored in ranked_scored_domains:
                                try:
                                    domain = None
                                    if isinstance(scored, dict):
                                        domain = scored.get('domain')
                                    else:
                                        # ScoredDomain object
                                        if hasattr(scored, 'domain'):
                                            domain = scored.domain
                                    
                                    if domain:
                                        ranked_domains_list.append(domain)
                                        
                                        # Ensure it's in the map for score lookup
                                        domain_name = None
                                        if isinstance(domain, dict):
                                            domain_name = domain.get('name')
                                        elif hasattr(domain, 'name'):
                                            domain_name = domain.name
                                        
                                        if domain_name:
                                            # Normalize domain name for consistent matching
                                            normalized_name = normalize_domain_name(domain_name)
                                            ranked_scored_map[normalized_name] = scored
                                except Exception as e:
                                    logger.warning("Failed to extract domain from scored", error=str(e))
                                    continue
                            
                            logger.info("Built ranked domains list and map", 
                                       extracted_count=len(ranked_domains_list),
                                       map_size=len(ranked_scored_map),
                                       sample_names=[d.name if hasattr(d, 'name') else d.get('name') if isinstance(d, dict) else 'unknown' for d in ranked_domains_list[:3]])
                        except Exception as e:
                            logger.warning("Failed to extract ranked domains", error=str(e), exc_info=True)
                            ranked_domains_list = []
            except Exception as e:
                logger.warning("Failed to process scored domains map", error=str(e), exc_info=True)
        
        # Use ranked domains if sorting by score or filtering by PASS, otherwise use all domains
        # But if filtering by FAIL, we need all domains to find failed ones
        # When using ranked domains for PASS filter, we can work directly with ScoredDomain objects
        use_scored_domains_directly = False
        if filter_status == 'FAIL':
            domains_to_filter = all_domains
        elif use_ranked_domains and ranked_scored_domains:
            # When filtering by PASS, we can use ScoredDomain objects directly
            # Extract domains from ScoredDomain objects but keep reference to scores
            domains_to_filter = []
            for scored in ranked_scored_domains:
                try:
                    domain = None
                    if isinstance(scored, dict):
                        domain = scored.get('domain')
                    else:
                        if hasattr(scored, 'domain'):
                            domain = scored.domain
                    
                    if domain:
                        domains_to_filter.append(domain)
                        # Ensure it's in the map
                        domain_name = None
                        if isinstance(domain, dict):
                            domain_name = domain.get('name')
                        elif hasattr(domain, 'name'):
                            domain_name = domain.name
                        
                        if domain_name:
                            # Normalize domain name for consistent matching
                            normalized_name = normalize_domain_name(domain_name)
                            ranked_scored_map[normalized_name] = scored
                except Exception as e:
                    logger.warning("Failed to extract domain from scored", error=str(e))
                    continue
        else:
            domains_to_filter = all_domains
        
        logger.info("Domain filtering", 
                   use_ranked=use_ranked_domains,
                   ranked_count=len(ranked_domains_list),
                   all_count=len(all_domains),
                   to_filter_count=len(domains_to_filter),
                   scored_map_size=len(scored_domains_map),
                   ranked_map_size=len(ranked_scored_map),
                   sort_by=sort_by,
                   filter_status=filter_status)
        
        # Apply filters
        filtered_domains = []
        for domain in domains_to_filter:
            domain_name = domain.name
            
            # Extension filter
            if extensions:
                extension_list = [ext.strip() for ext in extensions.split(',') if ext.strip()]
                if '.' in domain_name:
                    domain_ext = '.' + domain_name.split('.')[-1]
                    if domain_ext not in extension_list:
                        continue
                else:
                    continue
            
            # No special chars filter
            if no_special_chars:
                import re
                if re.search(r'[^a-zA-Z0-9.\-]', domain_name):
                    continue
            
            # No numbers filter
            if no_numbers:
                import re
                if re.search(r'\d', domain_name):
                    continue
            
            # Search filter
            if search and search.lower() not in domain_name.lower():
                continue
            
            # Filter by status (PASS/FAIL) - but skip if we're already using ranked domains (all PASS)
            # Only apply this filter if we're NOT using ranked domains for PASS
            if filter_status and filter_status in ['PASS', 'FAIL']:
                # If we're using ranked domains and filtering by PASS, skip this check (all are PASS)
                if not (use_ranked_domains and filter_status == 'PASS' and ranked_scored_domains):
                    # Normalize domain name for lookup
                    normalized_domain_name = normalize_domain_name(domain.name)
                    scored = scored_domains_map.get(normalized_domain_name) or ranked_scored_map.get(normalized_domain_name)
                    if scored:
                        # Handle both ScoredDomain objects and dicts
                        if isinstance(scored, dict):
                            status = scored.get('filter_status')
                        else:
                            status = scored.filter_status if hasattr(scored, 'filter_status') else None
                        
                        if status != filter_status:
                            continue
                    else:
                        # If no score data and filtering by PASS, skip it
                        if filter_status == 'PASS':
                            continue
                        # If filtering by FAIL and no score, include it (likely failed)
                        # This handles edge cases
            
            filtered_domains.append(domain)
        
        # Sort - handle score-based sorting
        reverse = (order == 'desc')
        
        # If we used ranked domains and sorting by score, they're already sorted by score DESC
        # Just reverse if needed
        if use_ranked_domains and ranked_domains_list and sort_by in ['total_meaning_score', 'rank']:
            # Domains are already sorted by score DESC from ranked_domains
            # Only reverse if order is 'asc'
            if order == 'asc':
                filtered_domains.reverse()
        elif sort_by in ['total_meaning_score', 'rank'] and scored_domains_map:
            # Fallback: sort using scored_domains_map
            domain_score_pairs = []
            for domain in filtered_domains:
                # Normalize domain name for lookup
                normalized_domain_name = normalize_domain_name(domain.name)
                scored = scored_domains_map.get(normalized_domain_name)
                if scored:
                    # Handle both ScoredDomain objects and dicts
                    if isinstance(scored, dict):
                        if sort_by == 'total_meaning_score':
                            score_value = scored.get('total_meaning_score', 0) or 0
                        elif sort_by == 'rank':
                            score_value = scored.get('rank', 999999) or 999999
                        else:
                            score_value = 0
                    else:
                        # ScoredDomain object
                        if sort_by == 'total_meaning_score':
                            score_value = scored.total_meaning_score if scored.total_meaning_score is not None else 0
                        elif sort_by == 'rank':
                            score_value = scored.rank if scored.rank is not None else 999999
                        else:
                            score_value = 0
                else:
                    score_value = 0 if sort_by == 'total_meaning_score' else 999999
                domain_score_pairs.append((domain, score_value))
            
            domain_score_pairs.sort(key=lambda x: x[1], reverse=reverse)
            filtered_domains = [d for d, _ in domain_score_pairs]
        else:
            # Regular sorting
            try:
                filtered_domains.sort(key=lambda d: getattr(d, sort_by, ''), reverse=reverse)
            except:
                # Fallback to name if sort field doesn't exist
                filtered_domains.sort(key=lambda d: d.name, reverse=reverse)
        
        # Paginate
        total_count = len(filtered_domains)
        paginated_domains = filtered_domains[offset:offset + limit]
        
        # Convert to dict format
        domains_list = []
        for idx, domain in enumerate(paginated_domains):
            try:
                # Generate stable ID based on domain name and index for CSV mode
                domain_id = domain.id or f"csv_{file_id}_{offset + idx}"
                
                # Helper function to safely format dates
                def format_date(dt):
                    if dt is None:
                        return None
                    try:
                        if isinstance(dt, str):
                            return dt
                        return dt.isoformat()
                    except Exception:
                        return None
                
                domain_dict = {
                    "id": domain_id,
                    "url": domain.url,
                    "name": domain.name,
                    "start_date": format_date(domain.start_date),
                    "end_date": format_date(domain.end_date),
                    "price": domain.price,
                    "start_price": domain.start_price,
                    "renew_price": domain.renew_price,
                    "bid_count": domain.bid_count,
                    "ahrefs_domain_rating": domain.ahrefs_domain_rating,
                    "umbrella_ranking": domain.umbrella_ranking,
                    "cloudflare_ranking": domain.cloudflare_ranking,
                    "estibot_value": domain.estibot_value,
                    "extensions_taken": domain.extensions_taken,
                    "keyword_search_count": domain.keyword_search_count,
                    "registered_date": format_date(domain.registered_date),
                    "last_sold_price": domain.last_sold_price,
                    "last_sold_year": domain.last_sold_year,
                    "is_partner_sale": domain.is_partner_sale,
                    "semrush_a_score": domain.semrush_a_score,
                    "majestic_citation": domain.majestic_citation,
                    "ahrefs_backlinks": domain.ahrefs_backlinks,
                    "semrush_backlinks": domain.semrush_backlinks,
                    "majestic_backlinks": domain.majestic_backlinks,
                    "majestic_trust_flow": domain.majestic_trust_flow,
                    "go_value": domain.go_value,
                }
                
                # Add scoring data if available
                try:
                    domain_name = domain.name
                    # Normalize domain name for consistent lookup
                    normalized_domain_name = normalize_domain_name(domain_name)
                    scored = None
                    
                    # Try ranked_scored_map first if using ranked domains
                    if ranked_scored_map:
                        scored = ranked_scored_map.get(normalized_domain_name)
                    
                    # Fallback to main scored_domains_map
                    if not scored and scored_domains_map:
                        scored = scored_domains_map.get(normalized_domain_name)
                    
                    # Debug: log first few domains to see if matching works
                    if idx < 10:
                        logger.info("Domain scoring lookup", 
                                   domain=domain_name,
                                   normalized=normalized_domain_name,
                                   found=scored is not None,
                                   use_ranked=use_ranked_domains,
                                   ranked_map_size=len(ranked_scored_map),
                                   main_map_size=len(scored_domains_map),
                                   ranked_map_keys_sample=list(ranked_scored_map.keys())[:5] if ranked_scored_map else [],
                                   main_map_keys_sample=list(scored_domains_map.keys())[:5] if scored_domains_map else [],
                                   has_score=scored is not None and (
                                       (isinstance(scored, dict) and scored.get('total_meaning_score') is not None) or
                                       (hasattr(scored, 'total_meaning_score') and scored.total_meaning_score is not None)
                                   ))
                    
                    if scored:
                        # Handle both ScoredDomain objects and dicts
                        if isinstance(scored, dict):
                            domain_dict["filter_status"] = scored.get("filter_status")
                            domain_dict["filter_reason"] = scored.get("filter_reason")
                            domain_dict["total_meaning_score"] = scored.get("total_meaning_score")
                            domain_dict["age_score"] = scored.get("age_score")
                            domain_dict["lexical_frequency_score"] = scored.get("lexical_frequency_score")
                            domain_dict["semantic_value_score"] = scored.get("semantic_value_score")
                            domain_dict["rank"] = scored.get("rank")
                        else:
                            # ScoredDomain object
                            domain_dict["filter_status"] = scored.filter_status
                            domain_dict["filter_reason"] = scored.filter_reason
                            domain_dict["total_meaning_score"] = scored.total_meaning_score
                            domain_dict["age_score"] = scored.age_score
                            domain_dict["lexical_frequency_score"] = scored.lexical_frequency_score
                            domain_dict["semantic_value_score"] = scored.semantic_value_score
                            domain_dict["rank"] = scored.rank
                    # If no match found, domain likely failed filtering (no score)
                    # This is expected for domains that didn't pass Stage 1 filtering
                except Exception as e:
                    logger.warning("Failed to add scoring data", domain=domain.name, error=str(e), exc_info=True)
                
                domains_list.append(domain_dict)
            except Exception as e:
                logger.error("Failed to process domain", domain=domain.name if hasattr(domain, 'name') else 'unknown', error=str(e), exc_info=True)
                continue
        
        # Convert dicts to NamecheapDomain objects
        domains_objects = []
        for d in domains_list:
            try:
                domain = NamecheapDomain(**d)
                domains_objects.append(domain)
            except Exception as e:
                logger.warning("Failed to create NamecheapDomain object", data=d, error=str(e))
                continue
        
        # Get scoring stats for response
        scoring_stats = None
        if scored_cache:
            scoring_stats = {
                "passed": scored_cache.get("passed_count", 0),
                "failed": scored_cache.get("failed_count", 0)
            }
        
        response = NamecheapDomainListResponse(
            success=True,
            count=len(domains_objects),
            domains=domains_objects,
            total_count=total_count,
            has_more=(offset + limit < total_count)
        )
        
        # Add scoring stats to response (convert to dict to include extra fields)
        response_dict = response.dict()
        if scoring_stats:
            response_dict["scoring_stats"] = scoring_stats
        
        return response_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get CSV domains", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve domains: {str(e)}")


@router.get("/namecheap/domains")
async def get_namecheap_domains(
    sort_by: str = Query("name", description="Field to sort by"),
    order: str = Query("asc", description="Sort order (asc, desc)"),
    search: Optional[str] = Query(None, description="Search filter for domain name"),
    extensions: Optional[str] = Query(None, description="Comma-separated list of extensions to filter (e.g., '.com,.net')"),
    no_special_chars: Optional[bool] = Query(None, description="Filter domains with no special characters"),
    no_numbers: Optional[bool] = Query(None, description="Filter domains with no numbers"),
    limit: int = Query(1000, description="Maximum number of records to return", ge=1, le=10000),
    offset: int = Query(0, description="Number of records to skip", ge=0)
):
    """
    Get all Namecheap domains with optional search, sorting, and filtering
    """
    try:
        db = get_database()
        # Parse extensions if provided
        extension_list = None
        if extensions:
            extension_list = [ext.strip() for ext in extensions.split(',') if ext.strip()]
        
        records = await db.get_all_namecheap_domains(
            sort_by=sort_by, 
            order=order, 
            search=search,
            extensions=extension_list,
            no_special_chars=no_special_chars,
            no_numbers=no_numbers,
            limit=limit,
            offset=offset
        )
        
        # Convert to dict format for JSON response
        result = []
        for record in records:
            record_dict = {
                "id": record.id,
                "url": record.url,
                "name": record.name,
                "start_date": record.start_date.isoformat() if record.start_date else None,
                "end_date": record.end_date.isoformat() if record.end_date else None,
                "price": record.price,
                "start_price": record.start_price,
                "renew_price": record.renew_price,
                "bid_count": record.bid_count,
                "ahrefs_domain_rating": record.ahrefs_domain_rating,
                "umbrella_ranking": record.umbrella_ranking,
                "cloudflare_ranking": record.cloudflare_ranking,
                "estibot_value": record.estibot_value,
                "extensions_taken": record.extensions_taken,
                "keyword_search_count": record.keyword_search_count,
                "registered_date": record.registered_date.isoformat() if record.registered_date else None,
                "last_sold_price": record.last_sold_price,
                "last_sold_year": record.last_sold_year,
                "is_partner_sale": record.is_partner_sale,
                "semrush_a_score": record.semrush_a_score,
                "majestic_citation": record.majestic_citation,
                "ahrefs_backlinks": record.ahrefs_backlinks,
                "semrush_backlinks": record.semrush_backlinks,
                "majestic_backlinks": record.majestic_backlinks,
                "majestic_trust_flow": record.majestic_trust_flow,
                "go_value": record.go_value,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None
            }
            result.append(record_dict)
        
        # Convert dicts to NamecheapDomain objects
        domains_list = []
        for r in result:
            try:
                domain = NamecheapDomain(**r)
                domains_list.append(domain)
            except Exception as e:
                logger.warning("Failed to create NamecheapDomain object", data=r, error=str(e))
                continue
        
        return NamecheapDomainListResponse(
            success=True,
            count=len(domains_list),
            domains=domains_list,
            total_count=len(records) if not (extensions or no_special_chars or no_numbers) else None,
            has_more=None
        )
        
    except Exception as e:
        logger.error("Failed to get Namecheap domains", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve domains: {str(e)}")


@router.post("/namecheap/analyze-selected", response_model=NamecheapAnalysisResponse)
async def analyze_selected_namecheap_domains(selection: NamecheapDomainSelection):
    """
    Analyze selected Namecheap domains
    
    For each domain:
    - Check if DataForSeo data exists in bulk_domain_analysis table
    - If exists: return it
    - If not: create record and trigger n8n webhook
    
    Returns combined Namecheap and DataForSeo data for each domain.
    """
    try:
        bulk_service = BulkAnalysisService()
        result = await bulk_service.analyze_selected_domains(selection.domain_names)
        
        # Convert Pydantic models to dict for JSON response
        results_dict = []
        for r in result.results:
            result_dict = {
                "domain": r.domain,
                "namecheap_data": r.namecheap_data.dict() if r.namecheap_data else None,
                "dataforseo_data": r.dataforseo_data.dict() if r.dataforseo_data else None,
                "has_data": r.has_data,
                "status": r.status,
                "error": r.error
            }
            results_dict.append(result_dict)
        
        return {
            "success": result.success,
            "results": results_dict,
            "total_selected": result.total_selected,
            "has_data_count": result.has_data_count,
            "triggered_count": result.triggered_count,
            "error_count": result.error_count
        }
        
    except Exception as e:
        logger.error("Failed to analyze selected domains", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to analyze domains: {str(e)}")


@router.post("/trigger-missing")
async def trigger_missing_summaries():
    """
    Manually trigger n8n webhook for domains missing summary data
    """
    try:
        bulk_service = BulkAnalysisService()
        result = await bulk_service.trigger_bulk_data_collection()
        
        return {
            "success": result.get("success", False),
            "triggered_count": result.get("triggered_count", 0),
            "domains": result.get("domains", []),
            "message": result.get("message", "Trigger completed")
        }
        
    except Exception as e:
        logger.error("Failed to trigger missing summaries", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to trigger: {str(e)}")


@router.get("/namecheap/scored-domains")
async def get_scored_domains(
    file_id: str = Query(..., description="File ID returned from upload"),
    limit: int = Query(1500, description="Maximum number of records to return", ge=1, le=5000),
    offset: int = Query(0, description="Number of records to skip", ge=0)
):
    """
    Get ranked domains with scores from cached CSV file
    """
    try:
        if file_id not in _csv_scored_cache:
            raise HTTPException(status_code=404, detail="Scored domains not found. File may have expired or not been scored.")
        
        cache_entry = _csv_scored_cache[file_id]
        ranked_domains = cache_entry.get("ranked_domains", [])  # Already sorted by score DESC
        
        # Paginate
        total_count = len(ranked_domains)
        paginated_domains = ranked_domains[offset:offset + limit]
        
        # Convert to dict format
        domains_list = []
        for scored in paginated_domains:
            domain = scored.domain
            # Generate stable ID based on domain name and rank for CSV mode
            domain_id = domain.id or f"csv_{file_id}_{scored.rank or 0}"
            domain_dict = {
                "id": domain_id,
                "url": domain.url,
                "name": domain.name,
                "start_date": domain.start_date.isoformat() if domain.start_date else None,
                "end_date": domain.end_date.isoformat() if domain.end_date else None,
                "price": domain.price,
                "start_price": domain.start_price,
                "renew_price": domain.renew_price,
                "bid_count": domain.bid_count,
                "ahrefs_domain_rating": domain.ahrefs_domain_rating,
                "umbrella_ranking": domain.umbrella_ranking,
                "cloudflare_ranking": domain.cloudflare_ranking,
                "estibot_value": domain.estibot_value,
                "extensions_taken": domain.extensions_taken,
                "keyword_search_count": domain.keyword_search_count,
                "registered_date": domain.registered_date.isoformat() if domain.registered_date else None,
                "last_sold_price": domain.last_sold_price,
                "last_sold_year": domain.last_sold_year,
                "is_partner_sale": domain.is_partner_sale,
                "semrush_a_score": domain.semrush_a_score,
                "majestic_citation": domain.majestic_citation,
                "ahrefs_backlinks": domain.ahrefs_backlinks,
                "semrush_backlinks": domain.semrush_backlinks,
                "majestic_backlinks": domain.majestic_backlinks,
                "majestic_trust_flow": domain.majestic_trust_flow,
                "go_value": domain.go_value,
                "filter_status": scored.filter_status,
                "filter_reason": scored.filter_reason,
                "total_meaning_score": scored.total_meaning_score,
                "age_score": scored.age_score,
                "lexical_frequency_score": scored.lexical_frequency_score,
                "semantic_value_score": scored.semantic_value_score,
                "rank": scored.rank
            }
            domains_list.append(domain_dict)
        
        # Convert to NamecheapDomain objects for response
        domains_objects = []
        for d in domains_list:
            try:
                domain = NamecheapDomain(**d)
                domains_objects.append(domain)
            except Exception as e:
                logger.warning("Failed to create NamecheapDomain object", data=d, error=str(e))
                continue
        
        return NamecheapDomainListResponse(
            success=True,
            count=len(domains_objects),
            domains=domains_objects,
            total_count=total_count,
            has_more=(offset + limit < total_count)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get scored domains", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve scored domains: {str(e)}")


@router.post("/namecheap/auto-trigger-analysis")
async def auto_trigger_analysis(
    file_id: str = Body(..., description="File ID returned from upload"),
    top_n: int = Body(1000, description="Number of top domains to consider"),
    top_rank_threshold: int = Body(3000, description="Rank threshold for top domains")
):
    """
    Auto-trigger DataForSEO analysis for top domains that meet criteria:
    1. Top N domains from ranked list
    2. Not in bulk_domain_analysis table
    3. In top 3000 of original CSV
    """
    try:
        if file_id not in _csv_scored_cache:
            raise HTTPException(status_code=404, detail="Scored domains not found. File may have expired.")
        
        cache_entry = _csv_scored_cache[file_id]
        ranked_domains = cache_entry.get("ranked_domains", [])
        top_3000_domains = cache_entry.get("top_3000_domains", [])
        
        if not ranked_domains:
            raise HTTPException(status_code=400, detail="No ranked domains available")
        
        # ranked_domains are already ScoredDomain objects, use directly
        scored_objects = ranked_domains
        
        # Trigger auto-analysis
        auto_trigger_service = AutoTriggerService()
        result = await auto_trigger_service.auto_trigger_analysis(
            ranked_domains=scored_objects,
            top_3000_domains=top_3000_domains,
            top_n=top_n,
            top_rank_threshold=top_rank_threshold
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to auto-trigger analysis", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to auto-trigger analysis: {str(e)}")
