"""
Filters & Saved Queries API routes
"""

from fastapi import APIRouter, HTTPException, Body, Query, Request
from typing import Optional, Dict, Any, List
import structlog
from pydantic import BaseModel
from datetime import date

from services.database import get_database

logger = structlog.get_logger()
router = APIRouter()


class FilterSettings(BaseModel):
    preferred: Optional[bool] = None
    auction_site: Optional[str] = None
    tld: Optional[str] = None
    tlds: Optional[List[str]] = None
    has_statistics: Optional[bool] = None
    scored: Optional[bool] = None
    min_rank: Optional[int] = None
    max_rank: Optional[int] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    keyword: Optional[str] = None
    expiration_from_date: Optional[str] = None
    expiration_to_date: Optional[str] = None
    sort_by: str = 'expiration_date'
    sort_order: str = 'asc'
    page_size: int = 50
    filter_name: Optional[str] = 'default'
    is_default: bool = False


class SavedQueryCreate(BaseModel):
    name: str
    query_params: Dict[str, Any]
    is_default: bool = False


class SavedQueryUpdate(BaseModel):
    name: Optional[str] = None
    query_params: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None


def _get_user_id(request: Request) -> Optional[str]:
    auth_header = request.headers.get('authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    try:
        import jwt
        token = auth_header.split(' ', 1)[1]
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload.get('sub')
    except Exception:
        return None


@router.get("/filters")
async def get_filters(user_id: Optional[str] = Query(None, description="Optional user ID, defaults to global filters")):
    try:
        db = get_database()
        if not db.client:
            raise HTTPException(status_code=503, detail="Database connection not available")

        result = (await db._get_client()).table('filters').select('*').eq('is_default', True)

        if user_id:
            result = result.eq('user_id', user_id)
        else:
            result = result.is_('user_id', 'null')

        result = await result.limit(1).execute()

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
                    "min_price": float(filter_data.get('min_price')) if filter_data.get('min_price') else None,
                    "max_price": float(filter_data.get('max_price')) if filter_data.get('max_price') else None,
                    "keyword": filter_data.get('keyword'),
                    "expiration_from_date": filter_data.get('expiration_from_date'),
                    "expiration_to_date": filter_data.get('expiration_to_date'),
                    "sort_by": filter_data.get('sort_by', 'expiration_date'),
                    "sort_order": filter_data.get('sort_order', 'asc'),
                    "page_size": filter_data.get('page_size', 50),
                    "filter_name": filter_data.get('filter_name', 'default'),
                }
            }
        else:
            return {
                "success": True,
                "filter": {
                    "preferred": None, "auction_site": None, "tld": None, "tlds": None,
                    "has_statistics": None, "scored": None, "min_rank": None, "max_rank": None,
                    "min_score": None, "max_score": None,
                    "min_price": None, "max_price": None, "keyword": None,
                    "expiration_from_date": None, "expiration_to_date": None,
                    "sort_by": "expiration_date", "sort_order": "asc",
                    "page_size": 50, "filter_name": "default",
                }
            }

    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to get filters", error=error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve filters: {error_msg}")


@router.put("/filters")
async def update_filters(filter_settings: FilterSettings, user_id: Optional[str] = Query(None, description="Optional user ID")):
    try:
        db = get_database()
        if not db.client:
            raise HTTPException(status_code=503, detail="Database connection not available")

        query = (await db._get_client()).table('filters').select('id').eq('is_default', True)
        if user_id:
            query = query.eq('user_id', user_id)
        else:
            query = query.is_('user_id', 'null')

        existing = await query.limit(1).execute()

        filter_data = {
            "preferred": filter_settings.preferred, "auction_site": filter_settings.auction_site,
            "tld": filter_settings.tld, "tlds": filter_settings.tlds,
            "has_statistics": filter_settings.has_statistics, "scored": filter_settings.scored,
            "min_rank": filter_settings.min_rank, "max_rank": filter_settings.max_rank,
            "min_score": filter_settings.min_score, "max_score": filter_settings.max_score,
            "min_price": filter_settings.min_price, "max_price": filter_settings.max_price,
            "keyword": filter_settings.keyword,
            "expiration_from_date": filter_settings.expiration_from_date,
            "expiration_to_date": filter_settings.expiration_to_date,
            "sort_by": filter_settings.sort_by, "sort_order": filter_settings.sort_order,
            "page_size": filter_settings.page_size,
            "filter_name": filter_settings.filter_name or 'default',
            "is_default": filter_settings.is_default,
        }

        if user_id:
            filter_data["user_id"] = user_id

        if existing.data and len(existing.data) > 0:
            filter_id = existing.data[0]['id']
            result = (await db._get_client()).table('filters').update(filter_data).eq('id', filter_id).execute()
            logger.info("Updated filter settings", filter_id=filter_id, user_id=user_id)
        else:
            result = (await db._get_client()).table('filters').insert(filter_data).execute()
            logger.info("Created new filter settings", user_id=user_id)

        return {"success": True, "message": "Filter settings saved successfully"}

    except Exception as e:
        error_msg = str(e)
        logger.error("Failed to update filters", error=error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save filters: {error_msg}")


# ─── Saved Queries CRUD ───

@router.get("/saved-queries")
async def list_saved_queries(request: Request):
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        db = get_database()
        if not db.client:
            raise HTTPException(status_code=503, detail="Database connection not available")

        result = await (await db._get_client()).table('saved_queries').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()

        return {
            "success": True,
            "queries": [
                {
                    "id": q['id'],
                    "name": q['name'],
                    "query_params": q.get('query_params', {}),
                    "is_default": q.get('is_default', False),
                    "created_at": q.get('created_at'),
                    "updated_at": q.get('updated_at'),
                }
                for q in (result.data or [])
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list saved queries", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list saved queries: {str(e)}")


@router.post("/saved-queries")
async def create_saved_query(body: SavedQueryCreate, request: Request):
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        db = get_database()
        if not db.client:
            raise HTTPException(status_code=503, detail="Database connection not available")

        if body.is_default:
            await (await db._get_client()).table('saved_queries').update({'is_default': False}).eq('user_id', user_id).eq('is_default', True).execute()

        result = await (await db._get_client()).table('saved_queries').insert({
            'user_id': user_id,
            'name': body.name,
            'query_params': body.query_params,
            'is_default': body.is_default,
        }).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create saved query")

        q = result.data[0]
        return {
            "success": True,
            "query": {
                "id": q['id'],
                "name": q['name'],
                "query_params": q.get('query_params', {}),
                "is_default": q.get('is_default', False),
                "created_at": q.get('created_at'),
                "updated_at": q.get('updated_at'),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create saved query", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create saved query: {str(e)}")


@router.put("/saved-queries/{query_id}")
async def update_saved_query(query_id: str, body: SavedQueryUpdate, request: Request):
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        db = get_database()
        if not db.client:
            raise HTTPException(status_code=503, detail="Database connection not available")

        existing = await (await db._get_client()).table('saved_queries').select('id').eq('id', query_id).eq('user_id', user_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Saved query not found")

        update_data = {}
        if body.name is not None:
            update_data['name'] = body.name
        if body.query_params is not None:
            update_data['query_params'] = body.query_params
        if body.is_default is not None:
            if body.is_default:
                await (await db._get_client()).table('saved_queries').update({'is_default': False}).eq('user_id', user_id).eq('is_default', True).execute()
            update_data['is_default'] = body.is_default

        if update_data:
            result = await (await db._get_client()).table('saved_queries').update(update_data).eq('id', query_id).eq('user_id', user_id).execute()
            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to update saved query")

            q = result.data[0]
            return {
                "success": True,
                "query": {
                    "id": q['id'], "name": q['name'],
                    "query_params": q.get('query_params', {}),
                    "is_default": q.get('is_default', False),
                    "created_at": q.get('created_at'), "updated_at": q.get('updated_at'),
                }
            }
        return {"success": True, "message": "No changes to apply"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update saved query", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update saved query: {str(e)}")


@router.delete("/saved-queries/{query_id}")
async def delete_saved_query(query_id: str, request: Request):
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        db = get_database()
        if not db.client:
            raise HTTPException(status_code=503, detail="Database connection not available")

        existing = await (await db._get_client()).table('saved_queries').select('id').eq('id', query_id).eq('user_id', user_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Saved query not found")

        await (await db._get_client()).table('saved_queries').delete().eq('id', query_id).eq('user_id', user_id).execute()

        return {"success": True, "message": "Saved query deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete saved query", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete saved query: {str(e)}")