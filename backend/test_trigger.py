
import asyncio
import os
import sys
from uuid import uuid4

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'backend/src'))

from services.database import init_database
from services.marketplace_batch_service import MarketplaceBatchService

async def test_trigger():
    await init_database()
    service = MarketplaceBatchService()
    
    user_id = uuid4() # Random user ID
    filters = {
        'scored': True
    }
    
    print(f"Triggering refresh in background for user {user_id}...")
    # This calls process_marketplace_refresh in background
    # We call it directly here to see the output
    await service.process_marketplace_refresh(
        user_id=user_id,
        filters=filters,
        force=False,
        job_id="test_job_123"
    )
    
    print("Refresh task completed. Checking /tmp/refresh_background.log...")
    if os.path.exists('/tmp/refresh_background.log'):
        with open('/tmp/refresh_background.log', 'r') as f:
            print(f.read())
    else:
        print("Log file not found!")

if __name__ == "__main__":
    asyncio.run(test_trigger())
