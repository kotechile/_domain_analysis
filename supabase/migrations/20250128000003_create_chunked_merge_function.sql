-- Create a function that merges a small chunk from staging and returns progress
-- This allows Python to call it repeatedly, avoiding single-transaction timeouts

CREATE OR REPLACE FUNCTION merge_auctions_chunk_from_staging(
    p_auction_site VARCHAR(100),
    p_chunk_size INTEGER DEFAULT 1000
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
    -- Check how many records remain
    SELECT COUNT(*) INTO v_remaining_count
    FROM auctions_staging
    WHERE auction_site = p_auction_site;
    
    IF v_remaining_count = 0 THEN
        RETURN jsonb_build_object(
            'success', true,
            'inserted', 0,
            'updated', 0,
            'processed', 0,
            'remaining', 0,
            'done', true
        );
    END IF;
    
    -- Merge one chunk from staging into auctions
    WITH chunk_staging AS (
        SELECT 
            domain,
            start_date,
            expiration_date,
            auction_site,
            current_bid,
            source_data,
            processed,
            preferred,
            has_statistics
        FROM auctions_staging
        WHERE auction_site = p_auction_site
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
            processed,
            preferred,
            has_statistics
        )
        SELECT 
            domain,
            start_date,
            expiration_date,
            auction_site,
            current_bid,
            source_data,
            processed,
            preferred,
            has_statistics
        FROM chunk_staging
        ON CONFLICT (domain, auction_site, expiration_date)
        DO UPDATE SET
            start_date = EXCLUDED.start_date,
            expiration_date = EXCLUDED.expiration_date,
            current_bid = EXCLUDED.current_bid,
            source_data = EXCLUDED.source_data,
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
    
    v_processed_count := v_inserted_count + v_updated_count;
    
    -- Delete processed records from staging using ctid (physical row identifier)
    -- This is more reliable than using domain/expiration_date which might have duplicates
    DELETE FROM auctions_staging
    WHERE auction_site = p_auction_site
    AND ctid IN (
        SELECT ctid
        FROM auctions_staging
        WHERE auction_site = p_auction_site
        ORDER BY domain, expiration_date
        LIMIT p_chunk_size
    );
    
    -- Check remaining count
    SELECT COUNT(*) INTO v_remaining_count
    FROM auctions_staging
    WHERE auction_site = p_auction_site;
    
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









