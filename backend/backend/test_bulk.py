import asyncio
import uuid
import sys
import os
os.environ['ALLOWED_ORIGINS'] = '["http://localhost:3010", "http://localhost:3011", "https://scout.buildomain.com"]'
os.environ['ALLOWED_HOSTS'] = '["localhost", "127.0.0.1"]'
os.environ['N8N_WEBHOOK_URL_BULK'] = 'https://n8n.giniloh.com/webhook/backlinks-bulk-page-summary'
from utils.config import get_settings
from services.marketplace_batch_service import MarketplaceBatchService

async def main():
    try:
        from services.database import init_database
        await init_database()
        service = MarketplaceBatchService()
        user_id = uuid.UUID("942d09c0-58ce-4fe5-b412-f16ac1694a72")
        res = await service.trigger_marketplace_refresh(user_id, {}, False)
        print("RESULT:", res)
    except Exception as e:
        print("EXCEPTION:", type(e))
        print("REPR:", repr(e))
        print("STR:", str(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
