import asyncio
import structlog
from src.services.database import init_database
from utils.config import get_settings

logger = structlog.get_logger()

async def main():
    user_id = "942d09c0-58ce-4fe5-b412-f16ac1694a72"

    # Initialize the database service properly
    try:
        db = await init_database()
        client = await db._get_client()

        # Update reports table for known domains that are missing user_id
        domains = ["giniloh.com", "code2cook.com", "google.com"]
        for domain in domains:
            await client.table('reports').update({'user_id': user_id}).eq('domain_name', domain).execute()
            logger.info("Updated report for domain", domain=domain)

        logger.info("User ID update completed successfully")

    except Exception as e:
        logger.error("Failed to update user IDs", error=str(e))

if __name__ == "__main__":
    asyncio.run(main())
