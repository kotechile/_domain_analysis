-- Add offer_type column to auctions and auctions_staging tables
-- This column stores the type of domain offering: 'auction', 'backorder', 'buy_now'
-- It is populated from the CSV filename when files are loaded

-- Add offer_type column to auctions table
ALTER TABLE auctions
ADD COLUMN IF NOT EXISTS offer_type VARCHAR(50);

-- Add offer_type column to auctions_staging table
ALTER TABLE auctions_staging
ADD COLUMN IF NOT EXISTS offer_type VARCHAR(50);

-- Create index for faster filtering by offer_type
CREATE INDEX IF NOT EXISTS idx_auctions_offer_type 
ON auctions(offer_type) 
WHERE offer_type IS NOT NULL;

-- Add comment
COMMENT ON COLUMN auctions.offer_type IS 'Type of domain offering: auction, backorder, buy_now';
COMMENT ON COLUMN auctions_staging.offer_type IS 'Type of domain offering: auction, backorder, buy_now';

-- Update merge function to include offer_type
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
    
    -- Merge one chunk from staging into auctions (now includes score, first_seen, deletion_flag, and offer_type)
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
            score,
            first_seen,
            deletion_flag,
            offer_type
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
            score,
            first_seen,
            deletion_flag,
            offer_type
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
            score,
            first_seen,
            deletion_flag,
            offer_type
        FROM chunk_staging
        ON CONFLICT (domain, auction_site, expiration_date)
        DO UPDATE SET
            start_date = EXCLUDED.start_date,
            expiration_date = EXCLUDED.expiration_date,
            current_bid = EXCLUDED.current_bid,
            source_data = EXCLUDED.source_data,
            processed = EXCLUDED.processed,
            -- Only update score if the new value is NOT NULL (preserve existing scores if new score is NULL)
            -- This prevents overwriting valid scores with NULL when re-uploading files
            score = COALESCE(EXCLUDED.score, auctions.score),
            first_seen = COALESCE(EXCLUDED.first_seen, auctions.first_seen),
            deletion_flag = EXCLUDED.deletion_flag,
            offer_type = EXCLUDED.offer_type,  -- Update offer_type on conflict
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

