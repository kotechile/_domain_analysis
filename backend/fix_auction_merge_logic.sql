-- FIX MERGE AUCTIONS DELTA FROM STAGING
-- 1. Removes the blanket DELETE that was wiping data during parallel imports.
-- 2. Uses UPSERT (ON CONFLICT DO UPDATE) to preserve existing record IDs and scores.
-- 3. Returns only truly NEW records (those with NULL score) for scoring.

CREATE OR REPLACE FUNCTION merge_auctions_delta_from_staging(
    p_auction_site VARCHAR,
    p_job_id VARCHAR,
    p_offering_type VARCHAR DEFAULT NULL,
    p_staging_table_suffix INTEGER DEFAULT NULL
)
RETURNS TABLE (
    domain TEXT,
    auction_site TEXT,
    expiration_date TIMESTAMPTZ,
    start_date TIMESTAMPTZ,
    current_bid DOUBLE PRECISION,
    link TEXT,
    offer_type TEXT,
    source_data JSONB,
    first_seen TEXT,
    is_new BOOLEAN
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_staging_table TEXT;
    v_job_id_uuid UUID;
BEGIN
    v_job_id_uuid := p_job_id::UUID;

    -- Determine staging table name
    IF p_staging_table_suffix IS NOT NULL THEN
        v_staging_table := 'auctions_staging_' || p_staging_table_suffix;
    ELSE
        v_staging_table := 'auctions_staging';
    END IF;

    -- RETURN QUERY EXECUTE using UPSERT logic
    -- We do NOT delete existing records anymore. 
    -- We UPSERT and let the Python sweep flag (to_delete) handle cleanup of truly missing records.
    
    RETURN QUERY EXECUTE format(
        'INSERT INTO auctions (
            domain, auction_site, expiration_date, start_date, current_bid, 
            link, offer_type, source_data, first_seen, to_delete, 
            score, processed, preferred, has_statistics
        )
        SELECT 
            s.domain, s.auction_site, s.expiration_date, s.start_date, s.current_bid, 
            s.link, s.offer_type, s.source_data, s.first_seen, FALSE, 
            s.score, FALSE, FALSE, FALSE
        FROM %I s
        WHERE s.job_id = $1
        ON CONFLICT (domain, auction_site, expiration_date) 
        DO UPDATE SET 
            current_bid = EXCLUDED.current_bid,
            source_data = EXCLUDED.source_data,
            link = EXCLUDED.link,
            to_delete = FALSE,
            updated_at = NOW()
        RETURNING 
            domain, 
            auction_site, 
            expiration_date, 
            start_date, 
            current_bid, 
            link, 
            offer_type, 
            source_data, 
            first_seen, 
            (score IS NULL)::BOOLEAN as is_new', -- If score is NULL, it means it was just inserted OR it didn't have a score before
        v_staging_table
    ) USING v_job_id_uuid;

    -- Cleanup staging records for this job
    EXECUTE format('DELETE FROM %I WHERE job_id = $1', v_staging_table) USING v_job_id_uuid;
END;
$$;
