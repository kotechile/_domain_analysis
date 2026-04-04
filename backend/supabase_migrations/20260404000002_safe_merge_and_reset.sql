-- Migration: Safe merge function with to_delete flag + reset stuck jobs
-- Run this in Supabase SQL Editor
-- Replaces the broken VARCHAR-cast-only fix with a proper to_delete-based approach

-- ============================================================
-- 1. Fix merge function: use to_delete flag for safe recovery
--    Problem: if DELETE runs but INSERT fails, all auction data for that site is lost.
--    Fix: mark records to_delete=TRUE first, insert new data, clear flag.
--    On conflict: update existing record and clear its to_delete flag.
--    Failed merges leave to_delete=TRUE records; call cleanup_stuck_upload() to remove them.
-- ============================================================
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
    v_deleted_count INTEGER := 0;
BEGIN
    IF p_staging_table_suffix IS NOT NULL THEN
        v_staging_table := 'auctions_staging_' || p_staging_table_suffix;
    ELSE
        v_staging_table := 'auctions_staging';
    END IF;

    -- Step 1: Mark all existing records for this site as "pending delete"
    IF p_offering_type IS NOT NULL AND p_auction_site NOT IN ('godaddy', 'namesilo') THEN
        UPDATE auctions
        SET to_delete = TRUE
        WHERE auction_site = p_auction_site
          AND (offer_type = p_offering_type OR (offer_type IS NULL AND p_offering_type IS NULL))
          AND to_delete = FALSE;
    ELSE
        UPDATE auctions
        SET to_delete = TRUE
        WHERE auction_site = p_auction_site
          AND to_delete = FALSE;
    END IF;
    GET DIAGNOSTICS v_deleted_count := ROW_COUNT;

    RAISE NOTICE 'Marked % stale records for deletion for site %.', v_deleted_count, p_auction_site;

    -- Step 2: Insert new records from staging
    -- On conflict: update existing and clear its to_delete flag (it's still live)
    -- NOT EXISTS: only insert truly new domains (those with no existing record at all)
    RETURN QUERY EXECUTE format(
        'INSERT INTO auctions (domain, auction_site, expiration_date, start_date, current_bid, link, offer_type, source_data, first_seen, to_delete, score, processed, preferred, has_statistics)
         SELECT
             s.domain::VARCHAR,
             s.auction_site::VARCHAR,
             s.expiration_date,
             s.start_date,
             s.current_bid,
             s.link::VARCHAR,
             s.offer_type::VARCHAR,
             s.source_data,
             s.first_seen,
             FALSE,  -- to_delete = FALSE (confirmed live)
             s.score,
             FALSE,
             FALSE,
             FALSE
         FROM %I s
         WHERE s.job_id = $1
           AND NOT EXISTS (
               SELECT 1 FROM auctions a
               WHERE a.domain = s.domain
                 AND a.auction_site = s.auction_site
                 AND a.expiration_date = s.expiration_date
           )
         ON CONFLICT (domain, auction_site, expiration_date) DO UPDATE
         SET start_date = EXCLUDED.start_date,
             current_bid = EXCLUDED.current_bid,
             link = EXCLUDED.link,
             offer_type = EXCLUDED.offer_type,
             source_data = EXCLUDED.source_data,
             to_delete = FALSE,
             updated_at = NOW()
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
             TRUE::BOOLEAN AS is_new',
        v_staging_table
    ) USING p_job_id;

    -- Step 3: Cleanup staging table
    EXECUTE format('DELETE FROM %I WHERE job_id = $1', v_staging_table) USING p_job_id;

    RAISE NOTICE 'Delta merge complete for %.', p_auction_site;
END;
$$;

GRANT EXECUTE ON FUNCTION merge_auctions_delta_from_staging TO service_role;

-- ============================================================
-- 2. Cleanup function: remove unrecovered (stale) auction records
--    after a failed merge. Also clears all staging tables.
--    Idempotent: safe to call multiple times.
-- ============================================================
DROP FUNCTION IF EXISTS cleanup_stuck_upload(UUID);

CREATE FUNCTION cleanup_stuck_upload(p_job_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_auction_site VARCHAR;
    v_offering_type VARCHAR;
    v_deleted_auctions INTEGER := 0;
    v_deleted_staging INTEGER := 0;
    v_cleaned_staging_tables TEXT[] := ARRAY[]::TEXT[];
BEGIN
    -- Get the job info
    SELECT auction_site, offering_type
    INTO v_auction_site, v_offering_type
    FROM csv_upload_progress
    WHERE job_id = p_job_id;

    IF v_auction_site IS NULL THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Job not found: ' || p_job_id
        );
    END IF;

    -- 1. Delete unrecovered auction records (to_delete = TRUE) for this site
    IF v_offering_type IS NOT NULL AND v_auction_site NOT IN ('godaddy', 'namesilo') THEN
        EXECUTE format(
            'DELETE FROM auctions WHERE auction_site = $1 AND (offer_type = $2 OR (offer_type IS NULL AND $2 IS NULL)) AND to_delete = TRUE',
            1, 2
        ) USING v_auction_site, v_offering_type;
    ELSE
        EXECUTE format(
            'DELETE FROM auctions WHERE auction_site = $1 AND to_delete = TRUE',
            1
        ) USING v_auction_site;
    END IF;
    GET DIAGNOSTICS v_deleted_auctions := ROW_COUNT;

    -- 2. Clear all staging tables for this job
    FOR i IN 0..4 LOOP
        EXECUTE format('DELETE FROM auctions_staging_%s WHERE job_id = $1', i) USING p_job_id;
        GET DIAGNOSTICS v_deleted_staging := ROW_COUNT;
        IF v_deleted_staging > 0 THEN
            v_cleaned_staging_tables := array_append(
                v_cleaned_staging_tables,
                format('auctions_staging_%s: %s rows', i, v_deleted_staging)
            );
        END IF;
    END LOOP;

    -- Also clear main staging table
    DELETE FROM auctions_staging WHERE job_id = p_job_id;
    GET DIAGNOSTICS v_deleted_staging := ROW_COUNT;
    IF v_deleted_staging > 0 THEN
        v_cleaned_staging_tables := array_append(
            v_cleaned_staging_tables,
            format('auctions_staging: %s rows', v_deleted_staging)
        );
    END IF;

    -- 3. Reset the job record
    UPDATE csv_upload_progress
    SET status = 'pending',
        current_stage = 'pending',
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
        'auction_site', v_auction_site,
        'deleted_auctions', v_deleted_auctions,
        'cleaned_staging', v_cleaned_staging_tables
    );
END;
$$;

GRANT EXECUTE ON FUNCTION cleanup_stuck_upload TO service_role;
