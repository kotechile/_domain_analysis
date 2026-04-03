-- Migration: Create optimized delta merge function
-- This function merges staging data into auctions and RETURNS only new domains for scoring
-- Existing domains keep their score, only new domains need scoring

CREATE OR REPLACE FUNCTION merge_auctions_delta_from_staging(
    p_job_id UUID,
    p_auction_site VARCHAR,
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
) AS $$
DECLARE
    v_deleted_count INTEGER := 0;
BEGIN
    -- =============================================
    -- PHASE 1: Mark old records for deletion
    -- =============================================
    -- For GoDaddy and NameSilo, we mark ALL records for cleanup
    -- For other sites, we respect offering_type
    IF p_auction_site IN ('godaddy', 'namesilo') THEN
        UPDATE auctions
        SET to_delete = TRUE
        WHERE auction_site = p_auction_site AND to_delete = FALSE;
    ELSE
        UPDATE auctions
        SET to_delete = TRUE
        WHERE auction_site = p_auction_site
          AND (offer_type = p_offering_type OR p_offering_type IS NULL)
          AND to_delete = FALSE;
    END IF;

    -- =============================================
    -- PHASE 2: Insert NEW domains (RETURNING for scoring)
    -- =============================================
    RETURN QUERY
    WITH inserted AS (
        INSERT INTO auctions (
            domain, auction_site, expiration_date, start_date,
            current_bid, link, offer_type, source_data,
            first_seen, to_delete, score, processed, preferred, has_statistics
        )
        SELECT
            s.domain,
            s.auction_site,
            s.expiration_date,
            s.start_date,
            s.current_bid,
            s.link,
            s.offer_type,
            s.source_data,
            s.first_seen,
            FALSE AS to_delete,
            s.score,  -- Will be NULL for new domains since we skip scoring
            FALSE AS processed,
            FALSE AS preferred,
            FALSE AS has_statistics
        FROM auctions_staging s
        WHERE s.job_id = p_job_id
          AND NOT EXISTS (
              SELECT 1 FROM auctions a
              WHERE a.domain = s.domain
                AND a.auction_site = s.auction_site
                AND a.expiration_date = s.expiration_date
          )
        ON CONFLICT (domain, auction_site, expiration_date)
        DO UPDATE SET
            start_date = EXCLUDED.start_date,
            current_bid = EXCLUDED.current_bid,
            link = EXCLUDED.link,
            offer_type = COALESCE(EXCLUDED.offer_type, auctions.offer_type),
            source_data = COALESCE(EXCLUDED.source_data, auctions.source_data),
            first_seen = COALESCE(EXCLUDED.first_seen, auctions.first_seen),
            to_delete = FALSE,
            updated_at = NOW()
        RETURNING
            auctions.domain,
            auctions.auction_site,
            auctions.expiration_date,
            auctions.start_date,
            auctions.current_bid,
            auctions.link,
            auctions.offer_type,
            auctions.source_data,
            auctions.first_seen
    )
    SELECT
        inserted.domain,
        inserted.auction_site,
        inserted.expiration_date,
        inserted.start_date,
        inserted.current_bid,
        inserted.link,
        inserted.offer_type,
        inserted.source_data,
        inserted.first_seen,
        TRUE::BOOLEAN AS is_new
    FROM inserted;

    -- =============================================
    -- PHASE 3: Update EXISTING domains (no score change)
    -- =============================================
    UPDATE auctions a
    SET
        start_date = COALESCE(s.start_date, a.start_date),
        current_bid = COALESCE(s.current_bid, a.current_bid),
        link = COALESCE(s.link, a.link),
        offer_type = COALESCE(s.offer_type, a.offer_type),
        source_data = COALESCE(s.source_data, a.source_data),
        first_seen = COALESCE(s.first_seen, a.first_seen),
        to_delete = FALSE,
        updated_at = NOW()
    FROM auctions_staging s
    WHERE s.job_id = p_job_id
      AND a.domain = s.domain
      AND a.auction_site = s.auction_site
      AND a.expiration_date = s.expiration_date
      AND a.to_delete = TRUE;  -- Only update ones we just marked

    -- =============================================
    -- PHASE 4: Delete merged records from staging
    -- =============================================
    DELETE FROM auctions_staging WHERE job_id = p_job_id;

    -- =============================================
    -- PHASE 5: Delete auctions marked for deletion (old stale records)
    -- =============================================
    DELETE FROM auctions WHERE auction_site = p_auction_site AND to_delete = TRUE;
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;

    RAISE NOTICE 'Delta merge complete. Deleted % stale records.', v_deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION merge_auctions_delta_from_staging TO service_role;
