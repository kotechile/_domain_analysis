-- Get new domains for scoring after import
-- Returns domains that were just inserted (have NULL score)

CREATE OR REPLACE FUNCTION get_new_domains_for_scoring(
    p_import_batch_id UUID,
    p_limit INTEGER DEFAULT 1000
)
RETURNS TABLE (
    domain TEXT,
    auction_site VARCHAR,
    expiration_date TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.domain::TEXT,
        a.auction_site::VARCHAR,
        a.expiration_date
    FROM auctions a
    WHERE a.last_import_batch_id = p_import_batch_id
      AND a.score IS NULL
    ORDER BY a.domain
    LIMIT p_limit;
END;
$$;

-- Add index to speed up "new domains" queries
CREATE INDEX IF NOT EXISTS idx_auctions_needs_scoring
ON auctions(last_import_batch_id)
WHERE score IS NULL;

-- Function to cleanup old import batches (to be run periodically)
CREATE OR REPLACE FUNCTION cleanup_old_import_batches(
    p_older_than_hours INTEGER DEFAULT 24
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_deleted INTEGER := 0;
BEGIN
    -- Delete old staging records
    DELETE FROM auctions_import
    WHERE import_timestamp < NOW() - (p_older_than_hours || ' hours')::INTERVAL;

    GET DIAGNOSTICS v_deleted = ROW_COUNT;

    RETURN jsonb_build_object(
        'success', true,
        'staging_records_deleted', v_deleted
    );
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM
    );
END;
$$;

-- Notify PostgREST
NOTIFY pgrst, 'reload schema';
