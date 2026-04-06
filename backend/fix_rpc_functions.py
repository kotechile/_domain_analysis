import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from services.database import DatabaseService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variable
load_dotenv()

async def run_fix():
    db = DatabaseService()
    client = await db._get_client()
    
    # 1. Clean up old versions to avoid ambiguity (42725)
    # We run these one by one because exec_sql might not support multiple statements
    cleanup_queries = [
        "DROP FUNCTION IF EXISTS merge_auctions_delta_from_staging(varchar, varchar, integer, varchar)",
        "DROP FUNCTION IF EXISTS merge_auctions_delta_from_staging(text, text, integer, text)",
        "DROP FUNCTION IF EXISTS merge_auctions_delta_from_staging(character varying, character varying, integer, character varying)",
        "DROP FUNCTION IF EXISTS cleanup_stuck_upload(varchar)",
        "DROP FUNCTION IF EXISTS cleanup_stuck_upload(text)"
    ]
    
    logger.info("Dropping old functions...")
    for q in cleanup_queries:
        try:
            await client.rpc('exec_sql', {'sql': q}).execute()
        except Exception as e:
            logger.debug(f"Note: {q} failed (probably didn't exist): {str(e)}")

    # 2. Create the NEW versions with SECURITY DEFINER and UPSERT logic
    # Using TEXT for all string params to avoid any future ambiguity
    merge_function_sql = """
CREATE OR REPLACE FUNCTION merge_auctions_delta_from_staging(
    p_job_id TEXT, 
    p_auction_site TEXT, 
    p_staging_table_suffix INTEGER DEFAULT NULL, 
    p_offering_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    domain TEXT, 
    auction_site TEXT, 
    expiration_date TIMESTAMPTZ, 
    start_date TIMESTAMPTZ, 
    current_bid NUMERIC, 
    link TEXT, 
    offer_type TEXT, 
    source_data JSONB, 
    first_seen TIMESTAMPTZ, 
    is_new BOOLEAN
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_staging_table TEXT;
    v_job_id_uuid UUID;
BEGIN
    -- Safe UUID cast
    BEGIN
        v_job_id_uuid := p_job_id::UUID;
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION 'Invalid job_id format: %', p_job_id;
    END;

    v_staging_table := CASE WHEN p_staging_table_suffix IS NOT NULL THEN 'auctions_staging_' || p_staging_table_suffix ELSE 'auctions_staging' END;
    
    RETURN QUERY EXECUTE format(
        'INSERT INTO auctions (domain, auction_site, expiration_date, start_date, current_bid, link, offer_type, source_data, first_seen, to_delete, score, processed, preferred, has_statistics, updated_at) ' ||
        'SELECT s.domain, s.auction_site, s.expiration_date, s.start_date, s.current_bid, s.link, s.offer_type, s.source_data, s.first_seen, FALSE, s.score, FALSE, FALSE, FALSE, NOW() ' ||
        'FROM %I s WHERE s.job_id = %L ' ||
        'ON CONFLICT (domain, auction_site, expiration_date) DO UPDATE ' ||
        'SET start_date = EXCLUDED.start_date, current_bid = EXCLUDED.current_bid, link = EXCLUDED.link, offer_type = EXCLUDED.offer_type, source_data = EXCLUDED.source_data, to_delete = FALSE, updated_at = NOW() ' ||
        'RETURNING (domain)::TEXT, (auction_site)::TEXT, expiration_date, start_date, current_bid, (link)::TEXT, (offer_type)::TEXT, source_data, first_seen, (score IS NULL)::BOOLEAN',
        v_staging_table, v_job_id_uuid
    );
    
    -- Cleanup staging
    EXECUTE format('DELETE FROM %I WHERE job_id = %L', v_staging_table, v_job_id_uuid);
END;
$$
    """

    cleanup_function_sql = """
CREATE OR REPLACE FUNCTION cleanup_stuck_upload(p_job_id TEXT)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    DELETE FROM auctions_staging WHERE job_id = p_job_id;
    DELETE FROM auctions_staging_0 WHERE job_id = p_job_id;
    DELETE FROM auctions_staging_1 WHERE job_id = p_job_id;
    DELETE FROM auctions_staging_2 WHERE job_id = p_job_id;
    DELETE FROM auctions_staging_3 WHERE job_id = p_job_id;
    DELETE FROM auctions_staging_4 WHERE job_id = p_job_id;
    UPDATE csv_upload_progress SET status = 'failed', error_message = 'Manually cleaned up' 
    WHERE job_id = p_job_id AND status IN ('pending', 'processing');
END;
$$
    """

    logger.info("Creating functions...")
    for sql in [merge_function_sql, cleanup_function_sql]:
        try:
            await client.rpc('exec_sql', {'sql': sql.strip()}).execute()
        except Exception as e:
            logger.error(f"Failed to create function: {str(e)}")
            # If it fails, print the SQL for debugging
            print(f"FAILED SQL:\n{sql}")

    # 3. Grants
    grants = [
        "GRANT EXECUTE ON FUNCTION merge_auctions_delta_from_staging(text, text, integer, text) TO anon",
        "GRANT EXECUTE ON FUNCTION merge_auctions_delta_from_staging(text, text, integer, text) TO authenticated",
        "GRANT EXECUTE ON FUNCTION merge_auctions_delta_from_staging(text, text, integer, text) TO service_role",
        "GRANT EXECUTE ON FUNCTION cleanup_stuck_upload(text) TO anon",
        "GRANT EXECUTE ON FUNCTION cleanup_stuck_upload(text) TO authenticated",
        "GRANT EXECUTE ON FUNCTION cleanup_stuck_upload(text) TO service_role"
    ]
    
    logger.info("Applying grants...")
    for g in grants:
        try:
            await client.rpc('exec_sql', {'sql': g}).execute()
        except Exception as e:
            logger.error(f"Failed to grant: {str(e)}")

    logger.info("Triggering schema reload...")
    try:
        await client.rpc('exec_sql', {'sql': "NOTIFY pgrst, 'reload schema'"}).execute()
    except:
        pass

    logger.info("Fix complete!")

if __name__ == "__main__":
    asyncio.run(run_fix())
