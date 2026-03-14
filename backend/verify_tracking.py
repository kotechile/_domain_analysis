import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# Load env vars from .env file
env_path = os.path.join(os.path.dirname(__file__), ".env")
print(f"Loading .env from {env_path}")
load_dotenv(env_path)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from services.database import DatabaseService

async def verify_tracking():
    """Verify that we can write to the user_resource_usage table"""
    try:
        logger.info("Initializing database service...")
        db = DatabaseService()
        
        if not db.client:
            logger.error("Failed to initialize database client")
            return

        logger.info("Testing insertion into user_resource_usage...")
        
        test_record = {
            'resource_type': 'test_resource',
            'operation': 'verify_tracking',
            'provider': 'test_provider',
            'model': 'test-model',
            'tokens_input': 10,
            'tokens_output': 20,
            'cost_estimated': 0.001,
            'details': {'test': True, 'verified_by': 'antigravity'}
        }
        
        # Insert without user_id (nullable) for system test
        result = db.client.table('user_resource_usage').insert(test_record).execute()
        
        if result.data:
            logger.info("Successfully inserted test record!")
            logger.info(f"Inserted Data: {result.data}")
            
            # Clean up
            record_id = result.data[0]['id']
            logger.info(f"Cleaning up test record {record_id}...")
            db.client.table('user_resource_usage').delete().eq('id', record_id).execute()
            logger.info("Cleanup complete.")
            
        else:
            logger.error("Insertion succeeded but returned no data?")
            
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_tracking())
