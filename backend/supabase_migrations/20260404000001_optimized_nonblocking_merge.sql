-- Migration: Fix merge function for type safety and remove blocking DELETE
-- Two fixes:
-- 1. link column: explicit ::VARCHAR casts in both SELECT and RETURNING
-- 2. Remove preliminary DELETE that causes statement timeouts on large datasets
--    (rely on INSERT...ON CONFLICT DO UPDATE for upserts instead)

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
    link VARCHAR,
    offer_type VARCHAR,
    source_data JSONB,
    first_seen TIMESTAMPTZ,
    is_new BOOLEAN
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_staging_table TEXT;
    v_inserted_count INTEGER := 0;
    v_updated_count INTEGER := 0;
BEGIN
    IF p_staging_table_suffix IS NOT NULL THEN
        v_staging_table := 'auctions_staging_' || p_staging_table_suffix;
    ELSE
        v_staging_table := 'auctions_staging';
    END IF;

    -- Step 1: INSERT new records (only if domain doesn't exist)
    -- This is fast because it only touches new records
    RETURN QUERY EXECUTE format(
        'INSERT INTO auctions (domain, auction_site, expiration_date, start_date, current_bid, link, offer_type, source_data, first_seen, to_delete, score, processed, preferred, has_statistics)
         SELECT
             s.domain::VARCHAR,
             s.auction_site::VARCHAR,
             s.expiration_date,
             s.start_date,
             s.current_bid,
             s.link::VARCHAR,
             COALESCE(s.offer_type, $2)::VARCHAR,
             s.source_data,
             s.first_seen,
             FALSE,
             s.score,
             FALSE,
             FALSE,
             FALSE
         FROM %I s
         WHERE s.job_id = $1
         ON CONFLICT (domain, auction_site, expiration_date) DO NOTHING
         RETURNING
             domain::VARCHAR,
             auction_site::VARCHAR,
             expiration_date,
             start_date,
             current_bid,
             link::VARCHAR,
             offer_type::VARCHAR,
             source_data,
             first_seen,
             TRUE AS is_new',
        v_staging_table
    ) USING p_job_id, p_offering_type;

    GET DIAGNOSTICS v_inserted_count = ROW_COUNT;
    RAISE NOTICE 'Inserted % new records for %', v_inserted_count, p_auction_site;

    -- Step 2: UPDATE existing records that are in staging
    -- This is an UPDATE, not DELETE+INSERT, so it's non-blocking
    -- Only updates the specific columns that can change (price, dates, link)
    RETURN QUERY EXECUTE format(
        'UPDATE auctions a SET
             start_date = s.start_date,
             current_bid = s.current_bid,
             link = s.link::VARCHAR,
             offer_type = COALESCE(s.offer_type, $2)::VARCHAR,
             source_data = s.source_data,
             to_delete = FALSE,
             updated_at = NOW()
         FROM %I s
         WHERE s.job_id = $1
           AND a.domain = s.domain
           AND a.auction_site = s.auction_site
           AND a.expiration_date = s.expiration_date
         RETURNING
             a.domain::VARCHAR,
             a.auction_site::VARCHAR,
             a.expiration_date,
             a.start_date,
             a.current_bid,
             a.link::VARCHAR,
             a.offer_type::VARCHAR,
             a.source_data,
             a.first_seen,
             FALSE AS is_new',
        v_staging_table
    ) USING p_job_id, p_offering_type;

    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RAISE NOTICE 'Updated % existing records for %', v_updated_count, p_auction_site;

    -- Clean up staging table
    EXECUTE format('DELETE FROM %I WHERE job_id = $1', v_staging_table) USING p_job_id;

    RAISE NOTICE 'Delta merge complete for %. New: %, Updated: %', p_auction_site, v_inserted_count, v_updated_count;
END;
$$;

GRANT EXECUTE ON FUNCTION merge_auctions_delta_from_staging TO service_role;
