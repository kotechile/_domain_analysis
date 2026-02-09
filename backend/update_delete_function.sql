-- SAFE DELETE EXPIRED AUCTIONS
-- Updates the function to avoid clearing the entire staging table, which disrupts concurrent imports.

CREATE OR REPLACE FUNCTION delete_expired_auctions()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_deleted_count INTEGER := 0;
BEGIN
    -- 1. Optimally, we DO NOT clear staging here blindly.
    -- Staging cleanup should be handled by the specific job that used it, or a separate "cleanup_stale_staging" function using timestamps.
    -- Removing the blunt DELETE FROM auctions_staging; prevents killing active imports.

    -- 2. Delete expired auctions
    -- Using a direct DELETE is often faster than CTE with RETURNING for massive deletions, 
    -- but RETURNING is good for counting.
    WITH deleted_rows AS (
        DELETE FROM auctions 
        WHERE expiration_date < NOW() 
        RETURNING 1
    )
    SELECT COUNT(*) INTO v_deleted_count FROM deleted_rows;
    
    RETURN v_deleted_count;
    
EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'Error in delete_expired_auctions: %', SQLERRM;
    RETURN 0;
END;
$$;
