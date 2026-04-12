-- Migration: stop rescoring already-attempted rows
-- Root cause: get_new_domains_for_scoring only filtered on score IS NULL,
-- so unsupported TLDs that intentionally keep score = NULL were fetched forever.

DROP FUNCTION IF EXISTS get_new_domains_for_scoring(UUID, INTEGER);

CREATE OR REPLACE FUNCTION get_new_domains_for_scoring(
    p_import_batch_id UUID DEFAULT NULL,
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
    WHERE a.score IS NULL
      AND COALESCE(a.processed, FALSE) = FALSE
      AND (p_import_batch_id IS NULL OR a.last_import_batch_id = p_import_batch_id)
    ORDER BY (a.last_import_batch_id = p_import_batch_id) DESC, a.domain
    LIMIT p_limit;
END;
$$;

COMMENT ON FUNCTION get_new_domains_for_scoring IS
'Returns domains that still need scoring; excludes rows already marked processed to prevent infinite rescoring loops.';

NOTIFY pgrst, 'reload schema';
