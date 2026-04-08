import asyncio
import structlog
from services.database import DatabaseService
from models.domain_analysis import DetailedDataType

logger = structlog.get_logger()

async def migrate_jsonb_to_relational():
    """
    Migrates existing detailed analysis data from JSONB blobs to relational tables.
    """
    db = DatabaseService()
    client = await db._get_client()

    # Data types to migrate
    types_to_migrate = [
        DetailedDataType.KEYWORDS,
        DetailedDataType.BACKLINKS,
        DetailedDataType.REFERRING_DOMAINS
    ]

    total_migrated_rows = 0

    for data_type in types_to_migrate:
        logger.info("Starting migration for data type", data_type=data_type.value)

        # Fetch all records of this type
        result = await client.table('detailed_analysis_data')\
            .select('*')\
            .eq('data_type', data_type.value)\
            .execute()

        if not result.data:
            logger.info("No data found to migrate for this type", data_type=data_type.value)
            continue

        logger.info("Found records to migrate", count=len(result.data), data_type=data_type.value)

        for record in result.data:
            domain = record['domain_name']
            json_data = record.get('json_data')

            if not json_data or 'items' not in json_data:
                continue

            items = json_data['items']
            if not items:
                continue

            try:
                await db.refresh_relational_detailed_data(domain, data_type, items)

                total_migrated_rows += len(items)
                logger.debug("Migrated items for domain", domain=domain, count=len(items))
            except Exception as e:
                logger.error("Failed to migrate domain", domain=domain, error=str(e))

    logger.info("Migration completed", total_rows_migrated=total_migrated_rows)

if __name__ == "__main__":
    asyncio.run(migrate_jsonb_to_relational())
