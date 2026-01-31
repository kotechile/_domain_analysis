-- Optimize delete_expired_auctions to use chunked deletion
-- This prevents timeouts by deleting only a subset of records at a time

CREATE OR REPLACE FUNCTION delete_expired_auctions()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_deleted_count INTEGER := 0;
BEGIN
    -- Delete records where expiration_date < NOW() with a limit
    -- Note: PostgreSQL DELETE doesn't support LIMIT directly, so we use CTE
    WITH deleted_rows AS (
        DELETE FROM auctions 
        WHERE id IN (
            SELECT id 
            FROM auctions 
            WHERE expiration_date < NOW() 
            LIMIT 10000 -- Limit to 10k records per call to prevent timeout
        )
        RETURNING 1
    )
    SELECT COUNT(*) INTO v_deleted_count FROM deleted_rows;
    
    RETURN v_deleted_count;
EXCEPTION WHEN OTHERS THEN
    -- Log error but don't fail
    RAISE WARNING 'Failed to delete expired auctions: %', SQLERRM;
    RETURN 0;
END;
$$;

-- Ensure index exists (idempotent)
CREATE INDEX IF NOT EXISTS idx_auctions_expiration ON auctions(expiration_date);

COMMENT ON FUNCTION delete_expired_auctions() IS 'Deletes up to 10,000 expired auctions. Run repeatedly to clear all.';
