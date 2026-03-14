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

async def create_exec_sql_function():
    """Create the exec_sql function in Supabase"""
    try:
        logger.info("Initializing database service...")
        db = DatabaseService()
        
        # SQL to create the exec_sql function
        # WARNING: This function allows arbitrary SQL execution.
        # It should only be accessible via service_role.
        sql = """
        CREATE OR REPLACE FUNCTION exec_sql(sql text)
        RETURNS jsonb
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        BEGIN
          EXECUTE sql;
          RETURN jsonb_build_object('status', 'success');
        EXCEPTION WHEN OTHERS THEN
          RETURN jsonb_build_object('status', 'error', 'message', SQLERRM);
        END;
        $$;
        
        -- Revoke all on function from public
        REVOKE ALL ON FUNCTION exec_sql(text) FROM public;
        -- Grant execute to service_role only
        GRANT EXECUTE ON FUNCTION exec_sql(text) TO service_role;
        """
        
        logger.info("Creating exec_sql function...")
        
        # We can't use rpc('exec_sql') to create exec_sql itself obviously.
        # If the user has a self-hosted supabase, maybe we can use the postgres connection directly?
        # But DatabaseService uses the HTTP API.
        
        # Wait, if DatabaseService._create_tables uses rpc('exec_sql'), it MUST have worked at some point.
        # How was it created initially?
        
        # I'll check if there's any other way. 
        # Actually, I'll try to use the httpx client to talk to the SQL API if available, 
        # but Supabase usually doesn't expose an "execute SQL" endpoint except via RPC.
        
        print("I need to create the exec_sql function in the Supabase SQL Editor manually or find another way.")
        print("However, I will try to see if I can use the postgres connection string from the .env file.")
        
    except Exception as e:
        logger.error(f"Failed: {str(e)}")

if __name__ == "__main__":
    # asyncio.run(create_exec_sql_function())
    pass
