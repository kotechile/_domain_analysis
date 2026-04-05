-- Complete fix for get_new_domains_for_scoring function
-- Run this entire block at once in Supabase SQL Editor

DROP FUNCTION IF EXISTS get_new_domains_for_scoring(UUID, INTEGER);

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

-- Notify PostgREST to reload schema
NOTIFY pgrst, 'reload schema';
