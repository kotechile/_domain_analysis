"""
Filters API routes for managing domain marketplace filter settings
"""

from fastapi import APIRouter, HTTPException, Body, Query
from typing import Optional, Dict, Any, List
import structlog
from pydantic import BaseModel
from datetime import date

from services.database import get_database

logger = structlog.get_logger()
router = APIRouter()


class FilterSettings(BaseModel):
    """Filter settings model"""
    preferred: Optional[bool] = None
    auction_site: Optional[str] = None
    tld: Optional[str] = None  # Deprecated: use tlds instead
    tlds: Optional[List[str]] = None  # Array of TLDs
    has_statistics: Optional[bool] = None
    scored: Optional[bool] = None
    min_rank: Optional[int] = None
    max_rank: Optional[int] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    expiration_from_date: Optional[str] = None  # Date string (YYYY-MM-DD)
    expiration_to_date: Optional[str] = None  # Date string (YYYY-MM-DD)
    sort_by: str = 'expiration_date'
    sort_order: str = 'asc'
    page_size: int = 50
    filter_name: Optional[str] = 'default'
    is_default: bool = False


@router.get("/filters")
async def get_filters(
    user_id: Optional[str] = Query(None, description="Optional user ID, defaults to global filters")
):
    """
    Get filter settings from database
    Returns default filter if user_id is not provided
    """
    try:
        db = get_database()
        if not db.client:
            raise HTTPException(status_code=503, detail="Database connection not available")
        
        # Get default filter (user_id is NULL for global defaults)
        result = db.client.table('filters').select('*').eq('is_default', True)
        
        if user_id:
            result = result.eq('user_id', user_id)
        else:
            result = result.is_('user_id', 'null')
        
        result = result.limit(1).execute()
        
        if result.data and len(result.data) > 0:
            filter_data = result.data[0]
            return {
                "success": True,
                "filter": {
                    "id": filter_data.get('id'),
                    "preferred": filter_data.get('preferred'),
                    "auction_site": filter_data.get('auction_site'),
                    "tld": filter_data.get('tld'),
                    "tlds": filter_data.get('tlds'),
                    "has_statistics": filter_data.get('has_statistics'),
                    "scored": filter_data.get('scored'),
                    "min_rank": filter_data.get('min_rank'),
                    "max_rank": filter_data.get('max_rank'),
                    "min_score": float(filter_data.get('min_score')) if filter_data.get('min_score') else None,
                    "max_score": float(filter_data.get('max_score')) if filter_data.get('max_score') else None,
                    "expiration_from_date": filter_data.get('expiration_from_date'),
                    "expiration_to_date": filter_data.get('expiration_to_date'),
                    "sort_by": filter_data.get('sort_by', 'expiration_date'),
                    "sort_order": filter_data.get('sort_order', 'asc'),
                    "page_size": filter_data.get('page_size', 50),
                    "filter_name": filter_data.get('filter_name', 'default'),
                }
            }
        else:
            # Return default values if no filter found
            return {
                "success": True,
                "filter": {
                    "preferred": None,
                    "auction_site": None,
                    "tld": None,
                    "tlds": None,
                    "has_statistics": None,
                    "scored": None,
                    "min_rank": None,
                    "max_rank": None,
                    "min_score": None,
                    "max_score": None,
                    "expiration_from_date": None,
                    "expiration_to_date": None,
                    "sort_by": "expiration_date",
                    "sort_order": "asc",
                    "page_size": 50,
                    "filter_name": "default",
                }
            }
            
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to get filters", error=error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve filters: {error_msg}")


@router.put("/filters")
async def update_filters(
    filter_settings: FilterSettings,
    user_id: Optional[str] = Query(None, description="Optional user ID")
):
    """
    Update or create filter settings
    If no filter exists, creates a new one. If exists, updates it.
    """
    try:
        db = get_database()
        if not db.client:
            raise HTTPException(status_code=503, detail="Database connection not available")
        
        # Check if default filter exists
        query = db.client.table('filters').select('id').eq('is_default', True)
        if user_id:
            query = query.eq('user_id', user_id)
        else:
            query = query.is_('user_id', 'null')
        
        existing = query.limit(1).execute()
        
        filter_data = {
            "preferred": filter_settings.preferred,
            "auction_site": filter_settings.auction_site,
            "tld": filter_settings.tld,
            "tlds": filter_settings.tlds,
            "has_statistics": filter_settings.has_statistics,
            "scored": filter_settings.scored,
            "min_rank": filter_settings.min_rank,
            "max_rank": filter_settings.max_rank,
            "min_score": filter_settings.min_score,
            "max_score": filter_settings.max_score,
            "expiration_from_date": filter_settings.expiration_from_date,
            "expiration_to_date": filter_settings.expiration_to_date,
            "sort_by": filter_settings.sort_by,
            "sort_order": filter_settings.sort_order,
            "page_size": filter_settings.page_size,
            "filter_name": filter_settings.filter_name or 'default',
            "is_default": filter_settings.is_default,
        }
        
        if user_id:
            filter_data["user_id"] = user_id
        
        if existing.data and len(existing.data) > 0:
            # Update existing filter
            filter_id = existing.data[0]['id']
            result = db.client.table('filters').update(filter_data).eq('id', filter_id).execute()
            logger.info("Updated filter settings", filter_id=filter_id, user_id=user_id)
        else:
            # Create new filter
            result = db.client.table('filters').insert(filter_data).execute()
            logger.info("Created new filter settings", user_id=user_id)
        
        return {
            "success": True,
            "message": "Filter settings saved successfully"
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to update filters", error=error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save filters: {error_msg}")














