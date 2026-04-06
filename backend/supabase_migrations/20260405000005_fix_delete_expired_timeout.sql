-- Fix: delete_expired_auctions timeout on large tables
-- Date: 2026-04-05
-- Issue: Unbounded DELETE causes statement timeout on millions of rows
-- Fix: Delete in chunks of 10000 with RETURNING to get count

DROP FUNCTION IF EXISTS delete_expired_auctions();

CREATE OR REPLACE FUNCTION delete_expired_auctions()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET statement_timeout = '300s'
AS $$
DECLARE
    v_deleted_count INTEGER := 0;
    v_batch_count INTEGER := 0;
    v_remaining INTEGER := 1;
BEGIN
    -- Delete in chunks to avoid statement timeout
    -- Each iteration deletes up to 10000 rows
    WHILE v_remaining > 0 LOOP
        DELETE FROM auctions
        WHERE ctid IN (
            SELECT ctid
            FROM auctions
            WHERE expiration_date < NOW()
            LIMIT 10000
        );

        GET DIAGNOSTICS v_batch_count = ROW_COUNT;
        v_deleted_count := v_deleted_count + v_batch_count;

        -- Exit if less than 10000 deleted (likely done or near the end)
        EXIT WHEN v_batch_count < 10000;
    END LOOP;

    RAISE NOTICE 'delete_expired_auctions: Deleted % total expired auctions.', v_deleted_count;
    RETURN v_deleted_count;
EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'Error in delete_expired_auctions: %', SQLERRM;
    RETURN v_deleted_count;
END;
$$;

COMMENT ON FUNCTION delete_expired_auctions IS 'Deletes expired auctions in chunks of 10k to avoid statement timeout';
