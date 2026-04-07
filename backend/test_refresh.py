
import asyncio
import os
import sys
from uuid import UUID

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.database import init_database, get_database
from services.marketplace_batch_service import MarketplaceBatchService

async def run():
    await init_database()
    service = MarketplaceBatchService()
    
    user_id = UUID('942d09c0-58ce-4fe5-b412-f16ac1694a72')
    filters = {
        "search": "",
        "min_score": 10
    }
    
    print(f"Triggering marketplace refresh for user {user_id}...")
    # process_marketplace_refresh(self, user_id: UUID, filters: Dict[str, Any], force: bool = False, job_id: str = None, 
    #                                  sort_by: str = None, sort_order: str = None, prioritized_domains: List[str] = None):
    
    await service.process_marketplace_refresh(
        user_id=user_id,
        filters=filters,
        force=True, # Force so we see action even if they had some old metrics
        sort_by="score",
        sort_order="desc"
    )
    
    print("Refresh trigger completed. Check logs/outputs.")

if __name__ == "__main__":
    asyncio.run(run())
