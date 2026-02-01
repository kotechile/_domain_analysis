import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from services.database import DatabaseService
from utils.config import get_settings
import logging
import os
from dotenv import load_dotenv

# Load env vars from .env file
env_path = os.path.join(os.path.dirname(__file__), ".env")
print(f"Loading .env from {env_path}")
load_dotenv(env_path)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
async def apply_migration():
    """Apply the consumption tracking migration"""
    try:
        logger.info("Initializing database service...")
        db = DatabaseService()
        
        # Read the SQL file
        migration_file = os.path.join(os.path.dirname(__file__), "consumption_tracking_migration.sql")
        if not os.path.exists(migration_file):
            logger.error(f"Migration file {migration_file} not found!")
            return
            
        with open(migration_file, "r") as f:
            sql_content = f.read()
            
        logger.info(f"Applying migration from {migration_file}...")
        
        # Split statements by semicolon to execute individually if needed, 
        # but supabase RPC usually handles blocks. 
        # Let's try executing the whole block first.
        
        # Note: The DatabaseService might not have a direct 'exec_sql' method exposed 
        # if it's using the supabase client directly for table operations.
        # Let's check if we can use the rpc method if established in previous steps.
        # Looking at `database.py` from previous turn:
        # line 137: result = self.client.rpc('exec_sql', {'sql': tables_sql})
        
        # So we expect an 'exec_sql' RPC function to exist in Supabase.
        
        response = db.client.rpc('exec_sql', {'sql': sql_content}).execute()
        
        logger.info("Migration applied successfully!")
        logger.info(f"Response: {response}")
        
    except Exception as e:
        logger.error(f"Failed to apply migration: {str(e)}")
        # If exec_sql RPC doesn't exist, we might need another way or prompt user.
        # But based on database.py, it seems relied upon.

if __name__ == "__main__":
    asyncio.run(apply_migration())
