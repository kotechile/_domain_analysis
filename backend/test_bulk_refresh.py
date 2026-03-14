import asyncio
from utils.config import get_settings
from services.marketplace_batch_service import MarketplaceBatchService

async def main():
    import uuid
    service = MarketplaceBatchService()
    user_id = uuid.UUID("942d09c0-58ce-4fe5-b412-f16ac1694a72")
    try:
        res = await service.trigger_marketplace_refresh(user_id, {}, False)
        print("RESULT:")
        print(res)
    except Exception as e:
        print("EXCEPTION:")
        print(repr(e))
        print(str(e))

asyncio.run(main())
