
-- Definitive fix for merge_auctions_delta_from_staging and cleanup_stuck_upload
-- This explicitly drops ALL variants to avoid ambiguity

-- =============================================
-- 1. DROP ALL VARIATIONS
-- =============================================
DROP FUNCTION IF EXISTS merge_auctions_delta_from_staging(UUID, VARCHAR, INTEGER, VARCHAR);
DROP FUNCTION IF EXISTS merge_auctions_delta_from_staging(UUID, VARCHAR, VARCHAR);
DROP FUNCTION IF EXISTS merge_auctions_delta_from_staging(VARCHAR, VARCHAR, INTEGER, VARCHAR); 
DROP FUNCTION IF EXISTS cleanup_stuck_upload(UUID);
DROP FUNCTION IF EXISTS cleanup_stuck_upload(VARCHAR);

-- =============================================
-- 2. CREATE merge_auctions_delta_from_staging
-- =============================================
CREATE OR REPLACE FUNCTION merge_auctions_delta_from_staging(
    p_job_id VARCHAR,
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
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_staging_table TEXT;
    v_job_id_uuid UUID;
BEGIN
    -- Cast VARCHAR to UUID safely
    BEGIN
        v_job_id_uuid := p_job_id::UUID;
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION 'Invalid job_id format: %', p_job_id;
    END;
    
    IF p_staging_table_suffix IS NOT NULL THEN
        v_staging_table := 'auctions_staging_' || p_staging_table_suffix;
    ELSE
        v_staging_table := 'auctions_staging';
    END IF;

    -- Delete existing records for this site/offering to fresh sync
    -- (We delete them because we are inserting the whole new state from staging)
    IF p_auction_site IN ('godaddy', 'namesilo') THEN
        DELETE FROM auctions WHERE auction_site = p_auction_site;
    ELSE
        IF p_offering_type IS NOT NULL THEN
            DELETE FROM auctions WHERE auction_site = p_auction_site 
            AND (offer_type = p_offering_type OR (offer_type IS NULL AND p_offering_type IS NULL));
        ELSE
            DELETE FROM auctions WHERE auction_site = p_auction_site;
        END IF;
    END IF;
    
    -- Insert from staging and return new records for scoring
    RETURN QUERY EXECUTE format(
        'INSERT INTO auctions (domain, auction_site, expiration_date, start_date, current_bid, link, offer_type, source_data, first_seen, to_delete, score, processed, preferred, has_statistics)
         SELECT s.domain, s.auction_site, s.expiration_date, s.start_date, s.current_bid, s.link, s.offer_type, s.source_data, s.first_seen, FALSE, s.score, FALSE, FALSE, FALSE
         FROM %I s
         WHERE s.job_id = $1
         ON CONFLICT (domain, auction_site, expiration_date) DO NOTHING
         RETURNING domain, auction_site, expiration_date, start_date, current_bid, link, offer_type, source_data, first_seen, TRUE::BOOLEAN',
        v_staging_table
    ) USING v_job_id_uuid;

    -- Cleanup staging records for this job
    EXECUTE format('DELETE FROM %I WHERE job_id = $1', v_staging_table) USING v_job_id_uuid;
END;
$$;

-- =============================================
-- 3. CREATE cleanup_stuck_upload
-- =============================================
CREATE OR REPLACE FUNCTION cleanup_stuck_upload(p_job_id VARCHAR)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_auction_site VARCHAR;
    v_offering_type VARCHAR;
    v_deleted_staging INTEGER := 0;
    v_total_deleted_staging INTEGER := 0;
    v_job_id_uuid UUID;
BEGIN
    -- Cast safety
    BEGIN
        v_job_id_uuid := p_job_id::UUID;
    EXCEPTION WHEN OTHERS THEN
        RETURN jsonb_build_object('success', false, 'error', 'Invalid job_id: ' || p_job_id);
    END;

    -- Get job details
    SELECT auction_site, offering_type INTO v_auction_site, v_offering_type 
    FROM csv_upload_progress WHERE job_id = p_job_id;
    
    IF v_auction_site IS NULL THEN 
        RETURN jsonb_build_object('success', false, 'error', 'Job not found: ' || p_job_id); 
    END IF;

    -- Cleanup staging tables (v0 to v4)
    FOR i IN 0..4 LOOP
        EXECUTE format('DELETE FROM auctions_staging_%s WHERE job_id = $1', i) USING v_job_id_uuid;
        GET DIAGNOSTICS v_deleted_staging := ROW_COUNT;
        v_total_deleted_staging := v_total_deleted_staging + v_deleted_staging;
    END LOOP;
    
    -- Cleanup main staging table
    DELETE FROM auctions_staging WHERE job_id = v_job_id_uuid;
    GET DIAGNOSTICS v_deleted_staging := ROW_COUNT;
    v_total_deleted_staging := v_total_deleted_staging + v_deleted_staging;

    -- Reset progress state
    UPDATE csv_upload_progress 
    SET status = 'pending', 
        current_stage = 'ready', 
        error_message = NULL, 
        processed_records = 0, 
        inserted_count = 0, 
        updated_count = 0, 
        skipped_count = 0, 
        deleted_expired_count = 0, 
        progress_percentage = '0.00', 
        completed_at = NULL, 
        updated_at = NOW() 
    WHERE job_id = p_job_id;

    RETURN jsonb_build_object(
        'success', true, 
        'job_id', p_job_id, 
        'deleted_staging_records', v_total_deleted_staging
    );
END;
$$;

-- =============================================
-- 4. GRANTS AND NOTIFY
-- =============================================
GRANT EXECUTE ON FUNCTION merge_auctions_delta_from_staging TO service_role;
GRANT EXECUTE ON FUNCTION cleanup_stuck_upload TO service_role;

-- Force PostgREST to reload its schema cache
NOTIFY pgrst, 'reload schema';
