-- Definitive fix: Ensure all RETURNING columns match RETURNS TABLE types exactly
-- The link column is TEXT in both auctions and auctions_staging tables
-- but the function RETURNS TABLE declares it as VARCHAR.
-- PostgreSQL is strict: RETURNING must match RETURNS TABLE column types exactly.
-- Fix: Explicitly cast every link reference to VARCHAR in the RETURNING clause.

DROP FUNCTION IF EXISTS merge_auctions_delta_from_staging(UUID, VARCHAR, INTEGER, VARCHAR);

CREATE FUNCTION merge_auctions_delta_from_staging(
    p_job_id UUID,
    p_auction_site VARCHAR,
    p_staging_table_suffix INTEGER DEFAULT NULL,
    p_offering_type VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    domain VARCHAR,
    auction_site VARCHAR,
    expiration_date TIMESTAMPTZ,
    start_date TIMESTAMPTZ,
    current_bid NUMERIC,
    link VARCHAR,          -- MUST be VARCHAR to match RETURNS TABLE
    offer_type VARCHAR,
    source_data JSONB,
    first_seen TIMESTAMPTZ,
    is_new BOOLEAN
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_staging_table TEXT;
    v_deleted_count INTEGER := 0;
BEGIN
    IF p_staging_table_suffix IS NOT NULL THEN
        v_staging_table := 'auctions_staging_' || p_staging_table_suffix;
    ELSE
        v_staging_table := 'auctions_staging';
    END IF;

    -- Delete expired records for godaddy/namesilo (they don't have offering_type)
    IF p_auction_site IN ('godaddy', 'namesilo') THEN
        DELETE FROM auctions WHERE auction_site = p_auction_site;
    ELSE
        -- For other sites (namecheap), optionally filter by offering_type
        IF p_offering_type IS NOT NULL THEN
            DELETE FROM auctions WHERE auction_site = p_auction_site AND (offer_type = p_offering_type OR (offer_type IS NULL AND p_offering_type IS NULL));
        ELSE
            DELETE FROM auctions WHERE auction_site = p_auction_site;
        END IF;
    END IF;
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    RAISE NOTICE 'Deleted % stale records for site %.', v_deleted_count, p_auction_site;

    -- Insert new/updated records from staging
    -- CRITICAL: All text columns that map to VARCHAR in RETURNS TABLE must be explicitly cast
    RETURN QUERY EXECUTE format(
        'INSERT INTO auctions (domain, auction_site, expiration_date, start_date, current_bid, link, offer_type, source_data, first_seen, to_delete, score, processed, preferred, has_statistics)
         SELECT s.domain, s.auction_site, s.expiration_date, s.start_date, s.current_bid, s.link::VARCHAR, s.offer_type::VARCHAR, s.source_data, s.first_seen, FALSE, s.score, FALSE, FALSE, FALSE
         FROM %I s
         WHERE s.job_id = $1
         ON CONFLICT (domain, auction_site, expiration_date) DO NOTHING
         RETURNING domain, auction_site, expiration_date, start_date, current_bid, link::VARCHAR, offer_type::VARCHAR, source_data, first_seen, TRUE',
        v_staging_table
    ) USING p_job_id;

    -- Clean up staging table
    EXECUTE format('DELETE FROM %I WHERE job_id = $1', v_staging_table) USING p_job_id;

    RAISE NOTICE 'Delta merge complete for %.', p_auction_site;
END;
$$;

GRANT EXECUTE ON FUNCTION merge_auctions_delta_from_staging TO service_role;
