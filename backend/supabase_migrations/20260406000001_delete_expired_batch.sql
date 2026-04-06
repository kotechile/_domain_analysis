-- Fix: Extract loops to python to prevent statement timeout
-- Date: 2026-04-06
-- Issue: Unbounded DELETE with internal LOOP causes 300s statement timeout on postgres execution

DROP FUNCTION IF EXISTS delete_expired_auctions();

CREATE OR REPLACE FUNCTION delete_expired_auctions_batch()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_batch_count INTEGER := 0;
BEGIN
    DELETE FROM auctions
    WHERE ctid IN (
        SELECT ctid
        FROM auctions
        WHERE expiration_date < NOW()
        LIMIT 10000
    );

    GET DIAGNOSTICS v_batch_count = ROW_COUNT;
    RETURN v_batch_count;
END;
$$;

COMMENT ON FUNCTION delete_expired_auctions_batch IS 'Deletes a single batch of 10k expired auctions. Meant to be looped by the backend.';
