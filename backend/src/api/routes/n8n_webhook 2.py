"""
N8N webhook endpoints for receiving workflow results
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import structlog
from pydantic import BaseModel, Field

from services.database import get_database
from models.domain_analysis import DetailedAnalysisData, DetailedDataType

logger = structlog.get_logger()
router = APIRouter()


class N8NBacklinksWebhookRequest(BaseModel):
    """Request model for N8N backlinks webhook"""
    request_id: str = Field(..., description="Unique request ID from trigger")
    domain: str = Field(..., description="Domain name analyzed")
    success: bool = Field(..., description="Whether the workflow succeeded")
    data: Optional[Dict[str, Any]] = Field(None, description="Backlink data if successful")
    error: Optional[str] = Field(None, description="Error message if failed")


@router.post("/n8n/webhook/backlinks")
async def receive_backlinks_webhook(request: N8NBacklinksWebhookRequest):
    """
    Receive backlink data from N8N workflow
    
    This endpoint is called by N8N after processing the backlinks request.
    """
    try:
        logger.info("Received N8N backlinks webhook", 
                   request_id=request.request_id,
                   domain=request.domain,
                   success=request.success)
        
        if not request.success:
            logger.error("N8N workflow failed", 
                        request_id=request.request_id,
                        domain=request.domain,
                        error=request.error)
            return {
                "success": False,
                "message": "Workflow failed",
                "error": request.error
            }
        
        if not request.data:
            logger.warning("N8N workflow succeeded but no data provided", 
                         request_id=request.request_id,
                         domain=request.domain)
            return {
                "success": False,
                "message": "No data provided in response"
            }
        
        # Validate and normalize data structure
        # Handle both summary data (backlinks, referring_domains, rank) and detailed data (items array)
        if "items" not in request.data:
            logger.info("N8N data appears to be summary format, normalizing structure", 
                       request_id=request.request_id,
                       domain=request.domain,
                       data_keys=list(request.data.keys()) if request.data else [])
            # Check if this is summary data (has backlinks, referring_domains, rank)
            if isinstance(request.data, dict):
                # Check if data is nested
                if "result" in request.data:
                    request.data = request.data["result"]
                elif "data" in request.data:
                    request.data = request.data["data"]
                
                # If it's summary data, preserve the structure but ensure compatibility
                if "backlinks" in request.data or "referring_domains" in request.data or "rank" in request.data:
                    # This is summary data - wrap it in a structure that matches detailed data format
                    # Keep the summary fields at the root level for compatibility
                    if "items" not in request.data:
                        # For summary data, we'll store it as-is but add an empty items array
                        # The summary metrics are preserved at the root level
                        request.data["items"] = []
                        logger.info("Normalized summary data structure", 
                                   request_id=request.request_id,
                                   domain=request.domain)
                else:
                    # Unknown format, wrap in items array
                    request.data = {"items": [request.data]}
        
        # Ensure items is a list
        if "items" in request.data and not isinstance(request.data["items"], list):
            request.data["items"] = [request.data["items"]]
        
        # Save to database
        db = get_database()
        detailed_data = DetailedAnalysisData(
            domain_name=request.domain,
            data_type=DetailedDataType.BACKLINKS,
            json_data=request.data
        )
        
        await db.save_detailed_data(detailed_data)
        
        logger.info("N8N backlinks data saved successfully", 
                   request_id=request.request_id,
                   domain=request.domain,
                   items_count=len(request.data.get("items", [])))
        
        return {
            "success": True,
            "message": "Backlinks data received and saved",
            "request_id": request.request_id,
            "domain": request.domain,
            "items_count": len(request.data.get("items", []))
        }
        
    except Exception as e:
        logger.error("Failed to process N8N webhook", 
                    request_id=request.request_id if hasattr(request, 'request_id') else None,
                    domain=request.domain if hasattr(request, 'domain') else None,
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook: {str(e)}"
        )


class N8NBacklinksSummaryWebhookRequest(BaseModel):
    """Request model for N8N backlinks summary webhook"""
    request_id: str = Field(..., description="Unique request ID from trigger")
    domain: str = Field(..., description="Domain name analyzed")
    success: bool = Field(..., description="Whether the workflow succeeded")
    data: Optional[Dict[str, Any]] = Field(None, description="Backlinks summary data if successful")
    error: Optional[str] = Field(None, description="Error message if failed")


@router.post("/n8n/webhook/backlinks-summary")
async def receive_backlinks_summary_webhook(request: N8NBacklinksSummaryWebhookRequest):
    """
    Receive backlinks summary data from N8N workflow
    
    This endpoint is called by N8N after processing the backlinks summary request.
    Summary data contains: backlinks, referring_domains, rank
    """
    try:
        logger.info("Received N8N backlinks summary webhook", 
                   request_id=request.request_id,
                   domain=request.domain,
                   success=request.success)
        
        if not request.success:
            logger.error("N8N summary workflow failed", 
                        request_id=request.request_id,
                        domain=request.domain,
                        error=request.error)
            return {
                "success": False,
                "message": "Workflow failed",
                "error": request.error
            }
        
        if not request.data:
            logger.warning("N8N summary workflow succeeded but no data provided", 
                         request_id=request.request_id,
                         domain=request.domain)
            return {
                "success": False,
                "message": "No data provided in response"
            }
        
        # Normalize summary data structure
        # DataForSEO response structure: { "tasks": [{ "result": [{ ... }] }] }
        summary_data = request.data
        
        # Handle nested structures from DataForSEO response
        if isinstance(summary_data, dict):
            # Check if it's the full DataForSEO response with tasks array
            if "tasks" in summary_data and isinstance(summary_data["tasks"], list) and len(summary_data["tasks"]) > 0:
                task = summary_data["tasks"][0]
                if "result" in task and isinstance(task["result"], list) and len(task["result"]) > 0:
                    summary_data = task["result"][0]
                elif "data" in task:
                    summary_data = task["data"]
            # Check if data is nested in result or data
            elif "result" in summary_data:
                if isinstance(summary_data["result"], list) and len(summary_data["result"]) > 0:
                    summary_data = summary_data["result"][0]
                else:
                    summary_data = summary_data["result"]
            elif "data" in summary_data:
                summary_data = summary_data["data"]
            
            # If it's still an array, take the first element (DataForSEO returns array)
            if isinstance(summary_data, list) and len(summary_data) > 0:
                summary_data = summary_data[0]
        
        # Save to database as raw data (for caching and later use)
        from services.database import get_database
        from models.domain_analysis import DataSource
        
        db = get_database()
        
        # Store summary data in raw_data format (for compatibility with existing code)
        raw_data = {
            "backlinks_summary": summary_data
        }
        
        await db.save_raw_data(domain_name=request.domain, api_source=DataSource.DATAFORSEO, data=raw_data)
        
        logger.info("N8N backlinks summary data saved successfully", 
                   request_id=request.request_id,
                   domain=request.domain,
                   backlinks=summary_data.get("backlinks", 0),
                   referring_domains=summary_data.get("referring_domains", 0),
                   rank=summary_data.get("rank", 0))
        
        return {
            "success": True,
            "message": "Backlinks summary data received and saved",
            "request_id": request.request_id,
            "domain": request.domain,
            "backlinks": summary_data.get("backlinks", 0),
            "referring_domains": summary_data.get("referring_domains", 0),
            "rank": summary_data.get("rank", 0)
        }
        
    except Exception as e:
        logger.error("Failed to process N8N summary webhook", 
                    request_id=request.request_id if hasattr(request, 'request_id') else None,
                    domain=request.domain if hasattr(request, 'domain') else None,
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook: {str(e)}"
        )


class N8NBulkPageSummaryWebhookRequest(BaseModel):
    """Request model for N8N bulk page summary webhook"""
    request_id: str = Field(..., description="Unique request ID from trigger")
    success: bool = Field(..., description="Whether the workflow succeeded")
    data: Optional[Dict[str, Any]] = Field(None, description="Bulk page summary data if successful")
    error: Optional[str] = Field(None, description="Error message if failed")


@router.post("/n8n/webhook/backlinks-bulk-page-summary")
async def receive_bulk_page_summary_webhook(request: N8NBulkPageSummaryWebhookRequest):
    """
    Receive bulk page summary data from N8N workflow
    
    This endpoint is called by N8N after processing the bulk page summary request.
    Expected format: {success: bool, data: {result: [{target: str, rank: int, backlinks: int, ...}, ...]}}
    """
    try:
        logger.info("Received N8N bulk page summary webhook", 
                   request_id=request.request_id,
                   success=request.success)
        
        if not request.success:
            logger.error("N8N bulk summary workflow failed", 
                        request_id=request.request_id,
                        error=request.error)
            return {
                "success": False,
                "message": "Workflow failed",
                "error": request.error
            }
        
        if not request.data:
            logger.warning("N8N bulk summary workflow succeeded but no data provided", 
                         request_id=request.request_id)
            return {
                "success": False,
                "message": "No data provided in response"
            }
        
        # Parse DataForSEO response structure
        # DataForSEO returns: {tasks: [{result: [{items: [{url: str, ...}, ...]}]}]}
        # n8n might send: {item: {items: [...]}} or {result: [{items: [...]}]} or {items: [...]}
        result_data = request.data
        
        logger.info("Parsing webhook data structure", 
                   data_keys=list(result_data.keys()) if isinstance(result_data, dict) else "not a dict",
                   data_type=type(result_data).__name__)
        
        # Handle various nested structures from n8n/DataForSEO
        if isinstance(result_data, dict):
            # Check for n8n wrapper: {item: {items: [...]}}
            if "item" in result_data and isinstance(result_data["item"], dict):
                item_obj = result_data["item"]
                logger.info("Found 'item' wrapper", 
                           item_keys=list(item_obj.keys()) if isinstance(item_obj, dict) else "not a dict")
                if "items" in item_obj and isinstance(item_obj["items"], list):
                    result_data = item_obj["items"]
                    logger.info("Extracted items from n8n item wrapper", 
                               item_count=len(result_data))
                elif isinstance(item_obj, dict):
                    # If item itself contains the data structure (fallback)
                    result_data = item_obj
                    logger.info("Using item object directly as result_data")
            # Check for DataForSEO structure: tasks[0].result[0].items
            elif "tasks" in result_data and isinstance(result_data["tasks"], list) and len(result_data["tasks"]) > 0:
                task = result_data["tasks"][0]
                if isinstance(task, dict) and "result" in task and isinstance(task["result"], list) and len(task["result"]) > 0:
                    result_obj = task["result"][0]
                    if isinstance(result_obj, dict) and "items" in result_obj:
                        result_data = result_obj["items"]
                        logger.info("Extracted items from DataForSEO tasks structure", 
                                   item_count=len(result_data) if isinstance(result_data, list) else 0)
                    elif isinstance(result_obj, dict):
                        result_data = [result_obj]
            # Check for direct result.items structure
            elif "result" in result_data:
                result_obj = result_data["result"]
                if isinstance(result_obj, list) and len(result_obj) > 0:
                    if isinstance(result_obj[0], dict) and "items" in result_obj[0]:
                        result_data = result_obj[0]["items"]
                    else:
                        result_data = result_obj
                elif isinstance(result_obj, dict) and "items" in result_obj:
                    result_data = result_obj["items"]
                else:
                    result_data = result_obj if isinstance(result_obj, list) else [result_obj]
            # Check for direct items array
            elif "items" in result_data:
                result_data = result_data["items"]
            # Check for nested data.result structure
            elif "data" in result_data and isinstance(result_data["data"], dict):
                if "result" in result_data["data"]:
                    result_obj = result_data["data"]["result"]
                    if isinstance(result_obj, list) and len(result_obj) > 0:
                        if isinstance(result_obj[0], dict) and "items" in result_obj[0]:
                            result_data = result_obj[0]["items"]
                        else:
                            result_data = result_obj
                    elif isinstance(result_obj, dict) and "items" in result_obj:
                        result_data = result_obj["items"]
                    else:
                        result_data = result_obj if isinstance(result_obj, list) else [result_obj]
                elif "items" in result_data["data"]:
                    result_data = result_data["data"]["items"]
        
        # Ensure result_data is a list
        if not isinstance(result_data, list):
            logger.warning("Expected list of results, got", 
                         data_type=type(result_data).__name__,
                         keys=list(result_data.keys()) if isinstance(result_data, dict) else None)
            result_data = [result_data] if result_data else []
        
        logger.info("Final result_data structure", 
                   is_list=isinstance(result_data, list),
                   item_count=len(result_data) if isinstance(result_data, list) else 0,
                   first_item_keys=list(result_data[0].keys()) if isinstance(result_data, list) and len(result_data) > 0 and isinstance(result_data[0], dict) else None)
        
        # Process each result
        db = get_database()
        processed_count = 0
        failed_count = 0
        failed_domains = []
        
        for result_item in result_data:
            try:
                if not isinstance(result_item, dict):
                    logger.warning("Invalid result item format", item_type=type(result_item).__name__)
                    failed_count += 1
                    continue
                
                # DataForSEO returns "url" field, but we also support "target" for compatibility
                target = result_item.get("target") or result_item.get("url")
                if not target:
                    logger.warning("Result item missing target/url field", item=result_item)
                    failed_count += 1
                    continue
                
                # Normalize domain (remove protocol if present, extract domain from URL)
                if isinstance(target, str):
                    # Remove http:// or https:// if present
                    target = target.replace("http://", "").replace("https://", "")
                    # Remove path if present (e.g., "example.com/path" -> "example.com")
                    target = target.split("/")[0]
                    # Remove www. if present
                    target = target.replace("www.", "")
                
                # Update page_statistics in auctions table
                success = False
                try:
                    success = await db.update_auction_page_statistics(domain=target, page_statistics=result_item)
                    if success:
                        logger.debug("Updated page_statistics in auctions table", domain=target)
                        
                        # Mark queue item as completed if it exists in queue
                        try:
                            await db.mark_queue_items_completed([target])
                        except Exception as queue_error:
                            # Not critical if queue item doesn't exist (might be admin-triggered batch)
                            logger.debug("Failed to mark queue item as completed (may not be in queue)", 
                                       domain=target, error=str(queue_error))
                    else:
                        logger.debug("Domain not found in auctions table", domain=target)
                except Exception as e:
                    # Not critical if domain doesn't exist in auctions table
                    logger.debug("Failed to update page_statistics in auctions table", domain=target, error=str(e))
                
                if success:
                    processed_count += 1
                    logger.info("Updated page_statistics in auctions table", 
                               domain=target,
                               rank=result_item.get("rank"),
                               backlinks=result_item.get("backlinks"))
                else:
                    failed_count += 1
                    failed_domains.append(target)
                    logger.warning("Failed to update page_statistics - domain not found in auctions table", 
                                 domain=target)
                
            except Exception as e:
                logger.error("Failed to process result item", 
                           target=result_item.get("target") if isinstance(result_item, dict) else None,
                           error=str(e))
                failed_count += 1
                if isinstance(result_item, dict) and result_item.get("target"):
                    failed_domains.append(result_item.get("target"))
        
        logger.info("Bulk page summary webhook processed", 
                   request_id=request.request_id,
                   processed=processed_count,
                   failed=failed_count,
                   total=len(result_data),
                   failed_domains=failed_domains[:10] if failed_domains else [])  # Log first 10 failed domains
        
        return {
            "success": True,
            "message": "Bulk page summary data received and saved",
            "request_id": request.request_id,
            "processed": processed_count,
            "failed": failed_count,
            "failed_domains": failed_domains
        }
        
    except Exception as e:
        logger.error("Failed to process N8N bulk summary webhook", 
                    request_id=request.request_id if hasattr(request, 'request_id') else None,
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook: {str(e)}"
        )


class N8NBulkRankWebhookRequest(BaseModel):
    """Request model for N8N bulk rank webhook"""
    request_id: str = Field(..., description="Unique request ID from trigger")
    success: bool = Field(..., description="Whether the workflow succeeded")
    data: Optional[Dict[str, Any]] = Field(None, description="Bulk rank data if successful")
    error: Optional[str] = Field(None, description="Error message if failed")


@router.post("/n8n/webhook/backlinks-bulk-rank")
async def receive_bulk_rank_webhook(request: N8NBulkRankWebhookRequest):
    """
    Receive bulk rank data from N8N workflow
    
    This endpoint is called by N8N after processing the bulk rank request.
    Expected format: {success: bool, data: {items: [{target: str, rank: int, ...}, ...]}}
    """
    try:
        logger.info("Received N8N bulk rank webhook", 
                   request_id=request.request_id,
                   success=request.success)
        
        if not request.success:
            logger.error("N8N bulk rank workflow failed", 
                        request_id=request.request_id,
                        error=request.error)
            return {
                "success": False,
                "message": "Workflow failed",
                "error": request.error
            }
        
        if not request.data:
            logger.warning("N8N bulk rank workflow succeeded but no data provided", 
                         request_id=request.request_id)
            return {
                "success": False,
                "message": "No data provided in response"
            }
        
        # Parse DataForSEO response structure
        # DataForSEO returns: {tasks: [{result: [{items: [{target: str, rank: int, ...}, ...]}]}]}
        result_data = request.data
        
        logger.info("Parsing bulk rank webhook data structure", 
                   data_keys=list(result_data.keys()) if isinstance(result_data, dict) else "not a dict",
                   data_type=type(result_data).__name__)
        
        # Handle various nested structures from n8n/DataForSEO (similar to bulk page summary)
        if isinstance(result_data, dict):
            # Check for n8n wrapper: {item: {items: [...]}}
            if "item" in result_data and isinstance(result_data["item"], dict):
                item_obj = result_data["item"]
                if "items" in item_obj and isinstance(item_obj["items"], list):
                    result_data = item_obj["items"]
                elif isinstance(item_obj, dict):
                    result_data = item_obj
            # Check for DataForSEO structure: tasks[0].result[0].items
            elif "tasks" in result_data and isinstance(result_data["tasks"], list) and len(result_data["tasks"]) > 0:
                task = result_data["tasks"][0]
                if isinstance(task, dict) and "result" in task and isinstance(task["result"], list) and len(task["result"]) > 0:
                    result_obj = task["result"][0]
                    if isinstance(result_obj, dict) and "items" in result_obj:
                        result_data = result_obj["items"]
                    elif isinstance(result_obj, dict):
                        result_data = [result_obj]
            # Check for direct result.items structure
            elif "result" in result_data:
                result_obj = result_data["result"]
                if isinstance(result_obj, list) and len(result_obj) > 0:
                    if isinstance(result_obj[0], dict) and "items" in result_obj[0]:
                        result_data = result_obj[0]["items"]
                    else:
                        result_data = result_obj
                elif isinstance(result_obj, dict) and "items" in result_obj:
                    result_data = result_obj["items"]
                else:
                    result_data = result_obj if isinstance(result_obj, list) else [result_obj]
            # Check for direct items array
            elif "items" in result_data:
                result_data = result_data["items"]
            # Check for nested data.result structure
            elif "data" in result_data and isinstance(result_data["data"], dict):
                if "result" in result_data["data"]:
                    result_obj = result_data["data"]["result"]
                    if isinstance(result_obj, list) and len(result_obj) > 0:
                        if isinstance(result_obj[0], dict) and "items" in result_obj[0]:
                            result_data = result_obj[0]["items"]
                        else:
                            result_data = result_obj
                    elif isinstance(result_obj, dict) and "items" in result_obj:
                        result_data = result_obj["items"]
                    else:
                        result_data = result_obj if isinstance(result_obj, list) else [result_obj]
                elif "items" in result_data["data"]:
                    result_data = result_data["data"]["items"]
        
        # Ensure result_data is a list
        if not isinstance(result_data, list):
            logger.warning("Expected list of results, got", 
                         data_type=type(result_data).__name__,
                         keys=list(result_data.keys()) if isinstance(result_data, dict) else None)
            result_data = [result_data] if result_data else []
        
        logger.info("Final bulk rank result_data structure", 
                   is_list=isinstance(result_data, list),
                   item_count=len(result_data) if isinstance(result_data, list) else 0,
                   first_item_keys=list(result_data[0].keys()) if isinstance(result_data, list) and len(result_data) > 0 and isinstance(result_data[0], dict) else None)
        
        # Process each result
        db = get_database()
        processed_count = 0
        failed_count = 0
        failed_domains = []
        
        for result_item in result_data:
            try:
                if not isinstance(result_item, dict):
                    logger.warning("Invalid result item format", item_type=type(result_item).__name__)
                    failed_count += 1
                    continue
                
                # DataForSEO returns "target" or "url" field
                target = result_item.get("target") or result_item.get("url")
                if not target:
                    logger.warning("Result item missing target/url field", item=result_item)
                    failed_count += 1
                    continue
                
                # Normalize domain (remove protocol if present, extract domain from URL)
                if isinstance(target, str):
                    # Remove http:// or https:// if present
                    target = target.replace("http://", "").replace("https://", "")
                    # Remove path if present (e.g., "example.com/path" -> "example.com")
                    target = target.split("/")[0]
                    # Remove www. if present
                    target = target.replace("www.", "")
                
                # Update page_statistics in auctions table with rank data
                # The update_auction_page_statistics method will merge with existing data
                success = False
                try:
                    success = await db.update_auction_page_statistics(domain=target, page_statistics=result_item)
                    if success:
                        logger.debug("Updated page_statistics with rank data in auctions table", domain=target)
                        
                        # Mark queue item as completed if it exists in queue
                        try:
                            await db.mark_queue_items_completed([target])
                        except Exception as queue_error:
                            # Not critical if queue item doesn't exist
                            logger.debug("Failed to mark queue item as completed (may not be in queue)", 
                                       domain=target, error=str(queue_error))
                    else:
                        logger.debug("Domain not found in auctions table", domain=target)
                except Exception as e:
                    # Not critical if domain doesn't exist in auctions table
                    logger.debug("Failed to update page_statistics in auctions table", domain=target, error=str(e))
                
                if success:
                    processed_count += 1
                    logger.info("Updated page_statistics with rank data in auctions table", 
                               domain=target,
                               rank=result_item.get("rank"))
                else:
                    failed_count += 1
                    failed_domains.append(target)
                    logger.warning("Failed to update page_statistics - domain not found in auctions table", 
                                 domain=target)
                
            except Exception as e:
                logger.error("Failed to process result item", 
                           target=result_item.get("target") if isinstance(result_item, dict) else None,
                           error=str(e))
                failed_count += 1
                if isinstance(result_item, dict) and result_item.get("target"):
                    failed_domains.append(result_item.get("target"))
        
        logger.info("Bulk rank webhook processed", 
                   request_id=request.request_id,
                   processed=processed_count,
                   failed=failed_count,
                   total=len(result_data),
                   failed_domains=failed_domains[:10] if failed_domains else [])  # Log first 10 failed domains
        
        return {
            "success": True,
            "message": "Bulk rank data received and saved",
            "request_id": request.request_id,
            "processed": processed_count,
            "failed": failed_count,
            "failed_domains": failed_domains
        }
        
    except Exception as e:
        logger.error("Failed to process N8N bulk rank webhook", 
                    request_id=request.request_id if hasattr(request, 'request_id') else None,
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook: {str(e)}"
        )


@router.post("/n8n/webhook/backlinks-bulk-backlinks")
async def receive_bulk_backlinks_webhook(request: N8NBulkRankWebhookRequest):
    """
    Receive bulk backlinks data from N8N workflow
    
    This endpoint is called by N8N after processing the bulk backlinks request.
    Expected format: {success: bool, data: {items: [{target: str, backlinks: int, referring_domains: int, ...}, ...]}}
    """
    try:
        logger.info("Received N8N bulk backlinks webhook", 
                   request_id=request.request_id,
                   success=request.success)
        
        if not request.success:
            logger.error("N8N bulk backlinks workflow failed", 
                        request_id=request.request_id,
                        error=request.error)
            return {
                "success": False,
                "message": "Workflow failed",
                "error": request.error
            }
        
        if not request.data:
            logger.warning("N8N bulk backlinks workflow succeeded but no data provided", 
                         request_id=request.request_id)
            return {
                "success": False,
                "message": "No data provided in response"
            }
        
        # Parse DataForSEO response structure
        # DataForSEO returns: {tasks: [{result: [{items: [{target: str, backlinks: int, referring_domains: int, ...}, ...]}]}]}
        result_data = request.data
        
        logger.info("Parsing bulk backlinks webhook data structure", 
                   data_keys=list(result_data.keys()) if isinstance(result_data, dict) else "not a dict",
                   data_type=type(result_data).__name__)
        
        # Handle various nested structures from n8n/DataForSEO (similar to bulk rank)
        if isinstance(result_data, dict):
            # Check for n8n wrapper: {item: {items: [...]}}
            if "item" in result_data and isinstance(result_data["item"], dict):
                item_obj = result_data["item"]
                if "items" in item_obj and isinstance(item_obj["items"], list):
                    result_data = item_obj["items"]
                elif isinstance(item_obj, list):
                    result_data = item_obj
            # Check for direct items array: {items: [...]}
            elif "items" in result_data and isinstance(result_data["items"], list):
                result_data = result_data["items"]
            # Check for tasks structure: {tasks: [{result: [{items: [...]}]}]}
            elif "tasks" in result_data and isinstance(result_data["tasks"], list) and len(result_data["tasks"]) > 0:
                task = result_data["tasks"][0]
                if "result" in task and isinstance(task["result"], list) and len(task["result"]) > 0:
                    result_obj = task["result"][0]
                    if "items" in result_obj and isinstance(result_obj["items"], list):
                        result_data = result_obj["items"]
                    elif isinstance(result_obj, list):
                        result_data = result_obj
        
        # Ensure result_data is a list
        if not isinstance(result_data, list):
            logger.warning("Bulk backlinks data is not a list, attempting to wrap", 
                         data_type=type(result_data).__name__)
            result_data = [result_data] if result_data else []
        
        db = get_database()
        processed_count = 0
        failed_count = 0
        failed_domains = []
        
        for result_item in result_data:
            try:
                if not isinstance(result_item, dict):
                    logger.warning("Invalid result item format", item_type=type(result_item).__name__)
                    failed_count += 1
                    continue
                
                # DataForSEO returns "target" or "url" field
                target = result_item.get("target") or result_item.get("url")
                if not target:
                    logger.warning("Result item missing target/url field", item=result_item)
                    failed_count += 1
                    continue
                
                # Normalize domain (remove protocol if present, extract domain from URL)
                if isinstance(target, str):
                    # Remove http:// or https:// if present
                    target = target.replace("http://", "").replace("https://", "")
                    # Remove path if present (e.g., "example.com/path" -> "example.com")
                    target = target.split("/")[0]
                    # Remove www. if present
                    target = target.replace("www.", "")
                
                # Update page_statistics in auctions table with backlinks data
                # The update_auction_page_statistics method will merge with existing data
                success = False
                try:
                    success = await db.update_auction_page_statistics(domain=target, page_statistics=result_item)
                    if success:
                        logger.debug("Updated page_statistics with backlinks data in auctions table", domain=target)
                        
                        # Mark queue item as completed if it exists in queue
                        try:
                            await db.mark_queue_items_completed([target])
                        except Exception as queue_error:
                            # Not critical if queue item doesn't exist
                            logger.debug("Failed to mark queue item as completed (may not be in queue)", 
                                       domain=target, error=str(queue_error))
                    else:
                        logger.debug("Domain not found in auctions table", domain=target)
                except Exception as e:
                    # Not critical if domain doesn't exist in auctions table
                    logger.debug("Failed to update page_statistics in auctions table", domain=target, error=str(e))
                
                if success:
                    processed_count += 1
                    logger.info("Updated page_statistics with backlinks data in auctions table", 
                               domain=target,
                               backlinks=result_item.get("backlinks"),
                               referring_domains=result_item.get("referring_domains"))
                else:
                    failed_count += 1
                    failed_domains.append(target)
                    logger.warning("Failed to update page_statistics - domain not found in auctions table", 
                                 domain=target)
                
            except Exception as e:
                logger.error("Failed to process result item", 
                           target=result_item.get("target") if isinstance(result_item, dict) else None,
                           error=str(e))
                failed_count += 1
                if isinstance(result_item, dict) and result_item.get("target"):
                    failed_domains.append(result_item.get("target"))
        
        logger.info("Bulk backlinks webhook processed", 
                   request_id=request.request_id,
                   processed=processed_count,
                   failed=failed_count,
                   total=len(result_data),
                   failed_domains=failed_domains[:10] if failed_domains else [])  # Log first 10 failed domains
        
        return {
            "success": True,
            "message": "Bulk backlinks data received and saved",
            "request_id": request.request_id,
            "processed": processed_count,
            "failed": failed_count,
            "failed_domains": failed_domains
        }
        
    except Exception as e:
        logger.error("Failed to process N8N bulk backlinks webhook", 
                    request_id=request.request_id if hasattr(request, 'request_id') else None,
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook: {str(e)}"
        )


@router.post("/n8n/webhook/backlinks-bulk-spam-score")
async def receive_bulk_spam_score_webhook(request: N8NBulkRankWebhookRequest):
    """
    Receive bulk spam score data from N8N workflow
    
    This endpoint is called by N8N after processing the bulk spam score request.
    Expected format: {success: bool, data: {items: [{target: str, backlinks_spam_score: int, ...}, ...]}}
    """
    try:
        logger.info("Received N8N bulk spam score webhook", 
                   request_id=request.request_id,
                   success=request.success)
        
        if not request.success:
            logger.error("N8N bulk spam score workflow failed", 
                        request_id=request.request_id,
                        error=request.error)
            return {
                "success": False,
                "message": "Workflow failed",
                "error": request.error
            }
        
        if not request.data:
            logger.warning("N8N bulk spam score workflow succeeded but no data provided", 
                         request_id=request.request_id)
            return {
                "success": False,
                "message": "No data provided in response"
            }
        
        # Parse DataForSEO response structure
        # DataForSEO returns: {tasks: [{result: [{items: [{target: str, backlinks_spam_score: int, ...}, ...]}]}]}
        result_data = request.data
        
        logger.info("Parsing bulk spam score webhook data structure", 
                   data_keys=list(result_data.keys()) if isinstance(result_data, dict) else "not a dict",
                   data_type=type(result_data).__name__)
        
        # Handle various nested structures from n8n/DataForSEO (similar to bulk rank/backlinks)
        if isinstance(result_data, dict):
            # Check for n8n wrapper: {item: {items: [...]}}
            if "item" in result_data and isinstance(result_data["item"], dict):
                item_obj = result_data["item"]
                if "items" in item_obj and isinstance(item_obj["items"], list):
                    result_data = item_obj["items"]
                elif isinstance(item_obj, list):
                    result_data = item_obj
            # Check for direct items array: {items: [...]}
            elif "items" in result_data and isinstance(result_data["items"], list):
                result_data = result_data["items"]
            # Check for tasks structure: {tasks: [{result: [{items: [...]}]}]}
            elif "tasks" in result_data and isinstance(result_data["tasks"], list) and len(result_data["tasks"]) > 0:
                task = result_data["tasks"][0]
                if "result" in task and isinstance(task["result"], list) and len(task["result"]) > 0:
                    result_obj = task["result"][0]
                    if "items" in result_obj and isinstance(result_obj["items"], list):
                        result_data = result_obj["items"]
                    elif isinstance(result_obj, list):
                        result_data = result_obj
        
        # Ensure result_data is a list
        if not isinstance(result_data, list):
            logger.warning("Bulk spam score data is not a list, attempting to wrap", 
                         data_type=type(result_data).__name__)
            result_data = [result_data] if result_data else []
        
        db = get_database()
        processed_count = 0
        failed_count = 0
        failed_domains = []
        
        for result_item in result_data:
            try:
                if not isinstance(result_item, dict):
                    logger.warning("Invalid result item format", item_type=type(result_item).__name__)
                    failed_count += 1
                    continue
                
                # DataForSEO returns "target" or "url" field
                target = result_item.get("target") or result_item.get("url")
                if not target:
                    logger.warning("Result item missing target/url field", item=result_item)
                    failed_count += 1
                    continue
                
                # Normalize domain (remove protocol if present, extract domain from URL)
                if isinstance(target, str):
                    # Remove http:// or https:// if present
                    target = target.replace("http://", "").replace("https://", "")
                    # Remove path if present (e.g., "example.com/path" -> "example.com")
                    target = target.split("/")[0]
                    # Remove www. if present
                    target = target.replace("www.", "")
                
                # Normalize DataForSEO field names to our internal format
                # DataForSEO returns "spam_score" but we store it as "backlinks_spam_score"
                normalized_result_item = result_item.copy()
                if "spam_score" in normalized_result_item and "backlinks_spam_score" not in normalized_result_item:
                    normalized_result_item["backlinks_spam_score"] = normalized_result_item.pop("spam_score")
                
                # Update page_statistics in auctions table with spam score data
                # The update_auction_page_statistics method will merge with existing data
                success = False
                try:
                    success = await db.update_auction_page_statistics(domain=target, page_statistics=normalized_result_item)
                    if success:
                        logger.debug("Updated page_statistics with spam score data in auctions table", domain=target)
                        
                        # Mark queue item as completed if it exists in queue
                        try:
                            await db.mark_queue_items_completed([target])
                        except Exception as queue_error:
                            # Not critical if queue item doesn't exist
                            logger.debug("Failed to mark queue item as completed (may not be in queue)", 
                                       domain=target, error=str(queue_error))
                    else:
                        logger.debug("Domain not found in auctions table", domain=target)
                except Exception as e:
                    # Not critical if domain doesn't exist in auctions table
                    logger.debug("Failed to update page_statistics in auctions table", domain=target, error=str(e))
                
                if success:
                    processed_count += 1
                    spam_score_value = normalized_result_item.get("backlinks_spam_score") or normalized_result_item.get("spam_score")
                    logger.info("Updated page_statistics with spam score data in auctions table", 
                               domain=target,
                               spam_score=spam_score_value)
                else:
                    failed_count += 1
                    failed_domains.append(target)
                    logger.warning("Failed to update page_statistics - domain not found in auctions table", 
                                 domain=target)
                
            except Exception as e:
                logger.error("Failed to process result item", 
                           target=result_item.get("target") if isinstance(result_item, dict) else None,
                           error=str(e))
                failed_count += 1
                if isinstance(result_item, dict) and result_item.get("target"):
                    failed_domains.append(result_item.get("target"))
        
        logger.info("Bulk spam score webhook processed", 
                   request_id=request.request_id,
                   processed=processed_count,
                   failed=failed_count,
                   total=len(result_data),
                   failed_domains=failed_domains[:10] if failed_domains else [])  # Log first 10 failed domains
        
        return {
            "success": True,
            "message": "Bulk spam score data received and saved",
            "request_id": request.request_id,
            "processed": processed_count,
            "failed": failed_count,
            "failed_domains": failed_domains
        }
        
    except Exception as e:
        logger.error("Failed to process N8N bulk spam score webhook", 
                    request_id=request.request_id if hasattr(request, 'request_id') else None,
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook: {str(e)}"
        )


@router.post("/n8n/webhook/backlinks-bulk-traffic-batch")
async def receive_bulk_traffic_batch_webhook(request: N8NBulkRankWebhookRequest):
    """
    Receive bulk traffic data from N8N workflow
    
    This endpoint is called by N8N after processing the bulk traffic batch request.
    Expected format: {success: bool, data: {items: [{target: str, traffic_data: {...}, ...}, ...]}}
    """
    try:
        logger.info("Received N8N bulk traffic batch webhook", 
                   request_id=request.request_id,
                   success=request.success)
        
        if not request.success:
            logger.error("N8N bulk traffic workflow failed", 
                        request_id=request.request_id,
                        error=request.error)
            return {
                "success": False,
                "message": "Workflow failed",
                "error": request.error
            }
        
        if not request.data:
            logger.warning("N8N bulk traffic workflow succeeded but no data provided", 
                         request_id=request.request_id)
            return {
                "success": False,
                "message": "No data provided in response"
            }
        
        # Parse DataForSEO response structure
        # DataForSEO Labs API returns traffic data in various formats
        result_data = request.data
        
        logger.info("Parsing bulk traffic webhook data structure", 
                   data_keys=list(result_data.keys()) if isinstance(result_data, dict) else "not a dict",
                   data_type=type(result_data).__name__)
        
        # Handle various nested structures from n8n/DataForSEO
        items = []
        if isinstance(result_data, dict):
            # Try different possible structures
            if 'items' in result_data:
                items = result_data['items']
            elif 'result' in result_data:
                if isinstance(result_data['result'], list) and len(result_data['result']) > 0:
                    if 'items' in result_data['result'][0]:
                        items = result_data['result'][0]['items']
                    else:
                        items = result_data['result']
            elif 'tasks' in result_data:
                # DataForSEO standard structure
                if isinstance(result_data['tasks'], list) and len(result_data['tasks']) > 0:
                    task = result_data['tasks'][0]
                    if 'result' in task and isinstance(task['result'], list) and len(task['result']) > 0:
                        if 'items' in task['result'][0]:
                            items = task['result'][0]['items']
                        else:
                            items = task['result']
        elif isinstance(result_data, list):
            items = result_data
        
        if not items:
            logger.warning("No items found in traffic data", 
                         request_id=request.request_id,
                         data_structure=list(result_data.keys()) if isinstance(result_data, dict) else "not a dict")
            return {
                "success": False,
                "message": "No items found in response data"
            }
        
        logger.info("Processing bulk traffic data", 
                   request_id=request.request_id,
                   item_count=len(items))
        
        db = get_database()
        processed_count = 0
        failed_count = 0
        failed_domains = []
        
        # Process each item
        for result_item in items:
            try:
                # Extract target domain
                target = None
                if isinstance(result_item, dict):
                    target = result_item.get('target') or result_item.get('domain') or result_item.get('url')
                    # Normalize domain (remove protocol, www, paths)
                    if target:
                        target = target.replace("http://", "").replace("https://", "")
                        target = target.split("/")[0]
                        target = target.replace("www.", "").strip().lower()
                
                if not target:
                    logger.warning("No target domain found in result item", 
                                 item_keys=list(result_item.keys()) if isinstance(result_item, dict) else "not a dict")
                    failed_count += 1
                    continue
                
                # Extract traffic data - store the entire result_item as traffic_data
                # This preserves all fields from DataForSEO Labs API
                traffic_data = result_item.copy() if isinstance(result_item, dict) else {"data": result_item}
                
                # Update traffic_data in auctions table
                success = False
                try:
                    success = await db.update_auction_traffic_data(domain=target, traffic_data=traffic_data)
                    if success:
                        logger.debug("Updated traffic_data in auctions table", domain=target)
                        
                        # Mark queue item as completed if it exists in queue
                        try:
                            await db.mark_queue_items_completed([target])
                        except Exception as queue_error:
                            # Not critical if queue item doesn't exist
                            logger.debug("Failed to mark queue item as completed (may not be in queue)", 
                                       domain=target, error=str(queue_error))
                    else:
                        logger.debug("Domain not found in auctions table", domain=target)
                except Exception as e:
                    # Not critical if domain doesn't exist in auctions table
                    logger.debug("Failed to update traffic_data in auctions table", domain=target, error=str(e))
                
                if success:
                    processed_count += 1
                    logger.info("Updated traffic_data in auctions table", 
                               domain=target)
                else:
                    failed_count += 1
                    failed_domains.append(target)
                    logger.warning("Failed to update traffic_data - domain not found in auctions table", 
                                 domain=target)
                
            except Exception as e:
                logger.error("Failed to process result item", 
                           target=result_item.get("target") if isinstance(result_item, dict) else None,
                           error=str(e))
                failed_count += 1
                if isinstance(result_item, dict) and result_item.get("target"):
                    failed_domains.append(result_item.get("target"))
        
        logger.info("Bulk traffic batch webhook processed", 
                   request_id=request.request_id,
                   processed=processed_count,
                   failed=failed_count,
                   total=len(items),
                   failed_domains=failed_domains[:10] if failed_domains else [])  # Log first 10 failed domains
        
        return {
            "success": True,
            "message": "Bulk traffic data received and saved",
            "request_id": request.request_id,
            "processed": processed_count,
            "failed": failed_count,
            "failed_domains": failed_domains
        }
        
    except Exception as e:
        logger.error("Failed to process N8N bulk traffic batch webhook", 
                    request_id=request.request_id if hasattr(request, 'request_id') else None,
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process webhook: {str(e)}"
        )


@router.get("/n8n/webhook/health")
async def n8n_webhook_health():
    """Health check endpoint for N8N webhook"""
    return {
        "status": "healthy",
        "service": "n8n_webhook"
    }

