"""
Debug endpoint to check offer_type values in database
"""
from fastapi import APIRouter
from services.database import get_database
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.get("/debug/offer-types")
async def debug_offer_types():
    """
    Debug endpoint to check what offer_type values exist in the database
    """
    try:
        db = get_database()
        
        # Query to get count of each offer_type
        result = db.client.table('auctions').select('offer_type', count='exact').execute()
        
        # Get sample records for each offer_type
        buy_now_sample = db.client.table('auctions').select('domain, offer_type').eq('offer_type', 'buy_now').limit(5).execute()
        auction_sample = db.client.table('auctions').select('domain, offer_type').eq('offer_type', 'auction').limit(5).execute()
        null_sample = db.client.table('auctions').select('domain, offer_type').is_('offer_type', 'null').limit(5).execute()
        
        # Count by offer_type using a raw query approach
        # Since Supabase doesn't support GROUP BY directly, we'll use RPC or count manually
        all_records = db.client.table('auctions').select('offer_type').limit(1000).execute()
        
        counts = {}
        for record in all_records.data:
            offer_type = record.get('offer_type') or 'NULL'
            counts[offer_type] = counts.get(offer_type, 0) + 1
        
        return {
            "success": True,
            "sample_counts": counts,
            "buy_now_samples": buy_now_sample.data if buy_now_sample.data else [],
            "auction_samples": auction_sample.data if auction_sample.data else [],
            "null_samples": null_sample.data if null_sample.data else [],
            "total_sampled": len(all_records.data) if all_records.data else 0
        }
    except Exception as e:
        logger.error("Failed to debug offer_types", error=str(e))
        return {
            "success": False,
            "error": str(e)
        }












