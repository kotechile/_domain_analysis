-- Create a more robust merge function that preserves statistics
-- Revision 20260302000000

CREATE OR REPLACE FUNCTION merge_auctions_chunk_from_staging_v2(
    p_auction_site VARCHAR(100),
    p_chunk_size INTEGER DEFAULT 1000,
    p_job_id VARCHAR(100) DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_inserted_count INTEGER := 0;
    v_updated_count INTEGER := 0;
    v_processed_count INTEGER := 0;
    v_remaining_count INTEGER := 0;
BEGIN
    -- 1. Merge one chunk from staging into auctions
    WITH chunk_staging AS (
        SELECT 
            domain,
            start_date,
            expiration_date,
            auction_site,
            current_bid,
            source_data,
            link,
            processed,
            preferred,
            has_statistics,
            score,
            offer_type,
            first_seen,
            deletion_flag,
            job_id
        FROM auctions_staging
        WHERE (p_auction_site IS NULL OR auction_site = p_auction_site)
          AND (p_job_id IS NULL OR job_id = p_job_id)
        ORDER BY domain, expiration_date
        LIMIT p_chunk_size
    ),
    merged AS (
        INSERT INTO auctions (
            domain,
            start_date,
            expiration_date,
            auction_site,
            current_bid,
            source_data,
            link,
            processed,
            preferred,
            has_statistics,
            score,
            offer_type,
            first_seen,
            deletion_flag
        )
        SELECT 
            domain,
            start_date,
            expiration_date,
            auction_site,
            current_bid,
            source_data,
            link,
            processed,
            preferred,
            has_statistics,
            score,
            offer_type,
            first_seen,
            deletion_flag
        FROM chunk_staging
        ON CONFLICT (domain, auction_site, expiration_date)
        DO UPDATE SET
            start_date = EXCLUDED.start_date,
            current_bid = EXCLUDED.current_bid,
            source_data = EXCLUDED.source_data,
            link = EXCLUDED.link,
            score = EXCLUDED.score,
            offer_type = EXCLUDED.offer_type,
            first_seen = COALESCE(EXCLUDED.first_seen, auctions.first_seen),
            updated_at = NOW()
        RETURNING 
            CASE WHEN xmax = 0 THEN 'inserted' ELSE 'updated' END as action
    ),
    action_counts AS (
        SELECT 
            COUNT(*) FILTER (WHERE action = 'inserted') as inserted,
            COUNT(*) FILTER (WHERE action = 'updated') as updated
        FROM merged
    )
    SELECT 
        inserted, updated
    INTO 
        v_inserted_count, v_updated_count
    FROM action_counts;
    
    v_processed_count := COALESCE(v_inserted_count, 0) + COALESCE(v_updated_count, 0);
    
    -- 2. Delete processed records from staging
    DELETE FROM auctions_staging
    WHERE ctid IN (
        SELECT ctid
        FROM auctions_staging
        WHERE (p_auction_site IS NULL OR auction_site = p_auction_site)
          AND (p_job_id IS NULL OR job_id = p_job_id)
        ORDER BY domain, expiration_date
        LIMIT p_chunk_size
    );
    
    -- 3. Check remaining count
    SELECT COUNT(*) INTO v_remaining_count
    FROM auctions_staging
    WHERE (p_auction_site IS NULL OR auction_site = p_auction_site)
      AND (p_job_id IS NULL OR job_id = p_job_id);
    
    RETURN jsonb_build_object(
        'success', true,
        'inserted', v_inserted_count,
        'updated', v_updated_count,
        'processed', v_processed_count,
        'remaining', v_remaining_count,
        'done', (v_remaining_count = 0)
    );
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_detail', PG_EXCEPTION_DETAIL,
        'processed', v_processed_count,
        'remaining', v_remaining_count
    );
END;
$$;
