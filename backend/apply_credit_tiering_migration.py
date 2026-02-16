import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from services.database import DatabaseService
from dotenv import load_dotenv
import logging

# Load env vars from .env file
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def apply_credit_tiering_migration():
    """Apply the credit tiering migration"""
    try:
        logger.info("Initializing database service...")
        db = DatabaseService()
        
        # Read the SQL file
        migration_file = os.path.join(os.path.dirname(__file__), "credit_tiering_migration.sql")
        if not os.path.exists(migration_file):
            logger.error(f"Migration file {migration_file} not found!")
            return
            
        with open(migration_file, "r") as f:
            sql_content = f.read()
            
        logger.info(f"Applying migration from {migration_file}...")
        
        # Note: We assume 'exec_sql' RPC exists in the Supabase DB
        response = db.client.rpc('exec_sql', {'sql': sql_content}).execute()
        
        logger.info("Migration applied successfully!")
        logger.info(f"Response: {response}")
        
    except Exception as e:
        logger.error(f"Failed to apply migration: {str(e)}")

if __name__ == "__main__":
    asyncio.run(apply_credit_tiering_migration())
