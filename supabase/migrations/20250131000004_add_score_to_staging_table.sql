-- Add score column to auctions_staging table
-- This allows scores to be passed through from CSV upload to main auctions table

ALTER TABLE auctions_staging
ADD COLUMN IF NOT EXISTS score DECIMAL(10,2);

-- Create index for score-based queries in staging
CREATE INDEX IF NOT EXISTS idx_auctions_staging_score ON auctions_staging(score) WHERE score IS NOT NULL;

-- Update merge function to include score
CREATE OR REPLACE FUNCTION merge_auctions_from_staging(
    p_auction_site VARCHAR(100)
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_inserted_count INTEGER := 0;
    v_updated_count INTEGER := 0;
    v_skipped_count INTEGER := 0;
    v_deleted_expired INTEGER := 0;
    v_total_staging INTEGER := 0;
BEGIN
    -- Count records in staging
    SELECT COUNT(*) INTO v_total_staging
    FROM auctions_staging
    WHERE auction_site = p_auction_site;
    
    IF v_total_staging = 0 THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'No records found in staging table for auction_site: ' || p_auction_site
        );
    END IF;
    
    -- Merge staging into auctions using INSERT ... ON CONFLICT
    -- This is much faster than individual upserts
    -- Now includes score field
    WITH merged AS (
        INSERT INTO auctions (
            domain,
            start_date,
            expiration_date,
            auction_site,
            current_bid,
            source_data,
            processed,
            preferred,
            has_statistics,
            score
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
            has_statistics,
            score
        FROM auctions_staging
        WHERE auction_site = p_auction_site
        ON CONFLICT (domain, auction_site, expiration_date)
        DO UPDATE SET
            start_date = EXCLUDED.start_date,
            expiration_date = EXCLUDED.expiration_date,
            current_bid = EXCLUDED.current_bid,
            source_data = EXCLUDED.source_data,
            processed = EXCLUDED.processed,
            score = EXCLUDED.score,  -- Update score on conflict
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
    
    -- Count skipped (if any validation issues)
    v_skipped_count := v_total_staging - v_inserted_count - v_updated_count;
    
    -- Delete expired records from auctions table
    DELETE FROM auctions WHERE expiration_date < NOW();
    GET DIAGNOSTICS v_deleted_expired = ROW_COUNT;
    
    -- Truncate staging table for this auction_site (cleanup)
    DELETE FROM auctions_staging WHERE auction_site = p_auction_site;
    
    RETURN jsonb_build_object(
        'success', true,
        'inserted', v_inserted_count,
        'updated', v_updated_count,
        'skipped', v_skipped_count,
        'deleted_expired', v_deleted_expired,
        'total_processed', v_total_staging,
        'auction_site', p_auction_site
    );
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_detail', PG_EXCEPTION_DETAIL,
        'total_processed', v_total_staging
    );
END;
$$;

-- Update chunked merge function to include score
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
    
    -- Merge one chunk from staging into auctions (now includes score)
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
            has_statistics,
            score
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
            has_statistics,
            score
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
            has_statistics,
            score
        FROM chunk_staging
        ON CONFLICT (domain, auction_site, expiration_date)
        DO UPDATE SET
            start_date = EXCLUDED.start_date,
            expiration_date = EXCLUDED.expiration_date,
            current_bid = EXCLUDED.current_bid,
            source_data = EXCLUDED.source_data,
            processed = EXCLUDED.processed,
            score = EXCLUDED.score,  -- Update score on conflict
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

-- Add comment
COMMENT ON COLUMN auctions_staging.score IS 'Domain score calculated during CSV upload (NULL if failed pre-screening)';

