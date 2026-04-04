-- Replace to_delete marking with direct DELETE + fresh INSERT
-- Avoids two full-table scans on large auctions table
-- Run this in Supabase SQL Editor

DROP FUNCTION IF EXISTS merge_auctions_delta_from_staging(UUID, VARCHAR, INTEGER, VARCHAR);

CREATE FUNCTION merge_auctions_delta_from_staging(
    p_job_id UUID,
    p_auction_site VARCHAR,
    p_staging_table_suffix INTEGER DEFAULT NULL,
    p_offering_type VARCHAR DEFAULT NULL
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
AS '
DECLARE
    v_staging_table TEXT;
    v_deleted_count INTEGER := 0;
BEGIN
    IF p_staging_table_suffix IS NOT NULL THEN
        v_staging_table := ''auctions_staging_'' || p_staging_table_suffix;
    ELSE
        v_staging_table := ''auctions_staging'';
    END IF;

    -- Direct DELETE instead of marking to_delete first
    -- This avoids scanning the entire auctions table twice
    IF p_offering_type IS NOT NULL AND p_auction_site NOT IN (''godaddy'', ''namesilo'') THEN
        EXECUTE format(
            ''DELETE FROM auctions WHERE auction_site = $1 AND (offer_type = $2 OR (offer_type IS NULL AND $2 IS NULL))'',
            1, 2
        ) USING p_auction_site, p_offering_type;
    ELSE
        EXECUTE format(
            ''DELETE FROM auctions WHERE auction_site = $1'',
            1
        ) USING p_auction_site;
    END IF;
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;

    RAISE NOTICE ''Deleted % stale records for site %.'', v_deleted_count, p_auction_site;

    -- All columns explicitly cast in both SELECT and RETURNING to match RETURNS TABLE types
    RETURN QUERY EXECUTE format(
        ''INSERT INTO auctions (domain, auction_site, expiration_date, start_date, current_bid, link, offer_type, source_data, first_seen, to_delete, score, processed, preferred, has_statistics)
         SELECT s.domain, s.auction_site, s.expiration_date, s.start_date, s.current_bid, s.link, s.offer_type, s.source_data, s.first_seen, FALSE, s.score, FALSE, FALSE, FALSE
         FROM %I s
         WHERE s.job_id = $1
         ON CONFLICT (domain, auction_site, expiration_date) DO NOTHING
         RETURNING domain, auction_site, expiration_date, start_date, current_bid, link, offer_type, source_data, first_seen, TRUE AS is_new'',
        v_staging_table
    ) USING p_job_id;

    -- Cleanup staging table
    EXECUTE format(''DELETE FROM %I WHERE job_id = $1'', v_staging_table) USING p_job_id;

    RAISE NOTICE ''Delta merge complete for %.'', p_auction_site;
END;
';

GRANT EXECUTE ON FUNCTION merge_auctions_delta_from_staging TO service_role;