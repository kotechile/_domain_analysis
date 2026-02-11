-- Update process_staging_data to be robust and handle all columns
-- This function merges data from auctions_staging to auctions for a specific job_id

CREATE OR REPLACE FUNCTION process_staging_data(
    p_job_id UUID,
    p_auction_site VARCHAR
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_inserted_count INTEGER := 0;
    v_updated_count INTEGER := 0;
    v_processed_count INTEGER := 0;
BEGIN
    -- Merge from staging into auctions
    -- We filter by job_id to only process records for this specific upload
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
            offer_type,
            link,
            job_id
        FROM auctions_staging
        WHERE job_id = p_job_id 
        AND auction_site = p_auction_site
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
            offer_type,
            link,
            job_id
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
            offer_type,
            link,
            job_id
        FROM chunk_staging
        ON CONFLICT (domain, auction_site, expiration_date)
        DO UPDATE SET
            start_date = EXCLUDED.start_date,
            expiration_date = EXCLUDED.expiration_date,
            current_bid = EXCLUDED.current_bid,
            source_data = EXCLUDED.source_data,
            processed = EXCLUDED.processed,
            -- Update score/first_seen only if new value is not null, preserving existing data
            score = COALESCE(EXCLUDED.score, auctions.score),
            first_seen = COALESCE(EXCLUDED.first_seen, auctions.first_seen),
            deletion_flag = EXCLUDED.deletion_flag,
            offer_type = EXCLUDED.offer_type,
            link = EXCLUDED.link,
            job_id = EXCLUDED.job_id,
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
        COALESCE(inserted, 0), COALESCE(updated, 0)
    INTO 
        v_inserted_count, v_updated_count
    FROM action_counts;
    
    -- Delete processed records from staging for this job
    DELETE FROM auctions_staging 
    WHERE job_id = p_job_id 
    AND auction_site = p_auction_site;
    
    RETURN jsonb_build_object(
        'success', true,
        'inserted', v_inserted_count,
        'updated', v_updated_count,
        'job_id', p_job_id
    );

EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_detail', PG_EXCEPTION_DETAIL
    );
END;
$$;
