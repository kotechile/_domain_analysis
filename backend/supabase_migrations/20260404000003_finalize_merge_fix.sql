-- Migration: Fix merge function performance with DISABLE TRIGGER + cleanup_stuck_upload
-- Problem: The update_auctions_updated_at trigger fires on every row during the
--          UPDATE SET to_delete = TRUE, causing 50s+ delays on 350K+ row tables.
-- Fix: DISABLE TRIGGER during the bulk UPDATE, then re-enable. Also increase timeout.
-- Also creates cleanup_stuck_upload() to atomically reset failed jobs.

-- Run this in Supabase SQL Editor

-- ============================================================
-- cleanup_stuck_upload: atomically clean up a failed upload job
-- ============================================================
DROP FUNCTION IF EXISTS cleanup_stuck_upload(VARCHAR);

CREATE FUNCTION cleanup_stuck_upload(p_job_id VARCHAR)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_auction_site VARCHAR; v_offering_type VARCHAR; v_deleted_auctions INTEGER := 0; v_deleted_staging INTEGER := 0; v_cleaned_staging_tables TEXT[] := ARRAY[]::TEXT[];
BEGIN
    SELECT auction_site, offering_type INTO v_auction_site, v_offering_type FROM csv_upload_progress WHERE job_id = p_job_id;
    IF v_auction_site IS NULL THEN RETURN jsonb_build_object('success', false, 'error', 'Job not found: ' || p_job_id); END IF;

    -- Disable updated_at trigger for bulk delete (massive speedup on large tables)
    ALTER TABLE auctions DISABLE TRIGGER update_auctions_updated_at;

    IF v_offering_type IS NOT NULL AND v_auction_site NOT IN ('godaddy', 'namesilo') THEN
        EXECUTE format('DELETE FROM auctions WHERE auction_site = $1 AND (offer_type = $2 OR (offer_type IS NULL AND $2 IS NULL)) AND to_delete = TRUE', 1, 2) USING v_auction_site, v_offering_type;
    ELSE
        EXECUTE format('DELETE FROM auctions WHERE auction_site = $1 AND to_delete = TRUE', 1) USING v_auction_site;
    END IF;
    GET DIAGNOSTICS v_deleted_auctions := ROW_COUNT;

    ALTER TABLE auctions ENABLE TRIGGER update_auctions_updated_at;

    FOR i IN 0..4 LOOP
        EXECUTE format('DELETE FROM auctions_staging_%s WHERE job_id = $1::UUID', i) USING p_job_id;
        GET DIAGNOSTICS v_deleted_staging := ROW_COUNT;
        IF v_deleted_staging > 0 THEN v_cleaned_staging_tables := array_append(v_cleaned_staging_tables, format('auctions_staging_%s: %s', i, v_deleted_staging)); END IF;
    END LOOP;
    DELETE FROM auctions_staging WHERE job_id = p_job_id::UUID;
    GET DIAGNOSTICS v_deleted_staging := ROW_COUNT;
    IF v_deleted_staging > 0 THEN v_cleaned_staging_tables := array_append(v_cleaned_staging_tables, format('auctions_staging: %s', v_deleted_staging)); END IF;

    UPDATE csv_upload_progress SET status = 'pending', current_stage = 'pending', error_message = NULL, processed_records = 0, inserted_count = 0, updated_count = 0, skipped_count = 0, deleted_expired_count = 0, progress_percentage = '0.00', completed_at = NULL, updated_at = NOW() WHERE job_id = p_job_id;
    RETURN jsonb_build_object('success', true, 'job_id', p_job_id, 'auction_site', v_auction_site, 'deleted_auctions', v_deleted_auctions, 'cleaned_staging', v_cleaned_staging_tables);
END;
$$;

GRANT EXECUTE ON FUNCTION cleanup_stuck_upload TO service_role;

-- ============================================================
-- merge_auctions_delta_from_staging: safe to_delete-based merge
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
SET statement_timeout = '120s'
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

    -- Disable the updated_at trigger for the bulk mark UPDATE (50s -> <1s on large tables)
    ALTER TABLE auctions DISABLE TRIGGER update_auctions_updated_at;

    -- Step 1: Mark stale records as pending delete
    IF p_offering_type IS NOT NULL AND p_auction_site NOT IN ('godaddy', 'namesilo') THEN
        UPDATE auctions SET to_delete = TRUE
        WHERE auction_site = p_auction_site
          AND (offer_type = p_offering_type OR (offer_type IS NULL AND p_offering_type IS NULL))
          AND to_delete = FALSE;
    ELSE
        UPDATE auctions SET to_delete = TRUE
        WHERE auction_site = p_auction_site AND to_delete = FALSE;
    END IF;
    GET DIAGNOSTICS v_deleted_count := ROW_COUNT;

    ALTER TABLE auctions ENABLE TRIGGER update_auctions_updated_at;

    RAISE NOTICE 'Marked % stale records for deletion for site %.', v_deleted_count, p_auction_site;

    -- Step 2: Insert new records; on conflict update existing and clear to_delete flag
    RETURN QUERY EXECUTE format(
        'INSERT INTO auctions (domain, auction_site, expiration_date, start_date, current_bid, link, offer_type, source_data, first_seen, to_delete, score, processed, preferred, has_statistics)
         SELECT s.domain::VARCHAR, s.auction_site::VARCHAR, s.expiration_date, s.start_date, s.current_bid, s.link::VARCHAR, s.offer_type::VARCHAR, s.source_data, s.first_seen, FALSE, s.score, FALSE, FALSE, FALSE
         FROM %I s WHERE s.job_id = $1
           AND NOT EXISTS (SELECT 1 FROM auctions a WHERE a.domain = s.domain AND a.auction_site = s.auction_site AND a.expiration_date = s.expiration_date)
         ON CONFLICT (domain, auction_site, expiration_date) DO UPDATE
         SET start_date = EXCLUDED.start_date, current_bid = EXCLUDED.current_bid, link = EXCLUDED.link,
             offer_type = EXCLUDED.offer_type, source_data = EXCLUDED.source_data, to_delete = FALSE, updated_at = NOW()
         RETURNING domain::VARCHAR, auction_site::VARCHAR, expiration_date, start_date, current_bid, link::VARCHAR, offer_type::VARCHAR, source_data, first_seen, TRUE::BOOLEAN AS is_new',
        v_staging_table
    ) USING p_job_id;

    -- Step 3: Cleanup staging table
    EXECUTE format('DELETE FROM %I WHERE job_id = $1', v_staging_table) USING p_job_id;

    RAISE NOTICE 'Delta merge complete for %.', p_auction_site;
END;
$$;

GRANT EXECUTE ON FUNCTION merge_auctions_delta_from_staging TO service_role;

-- ============================================================
-- Indexes to speed up the to_delete UPDATE
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_auctions_auction_site ON auctions(auction_site);
CREATE INDEX IF NOT EXISTS idx_auctions_site_notdeleted ON auctions(auction_site, to_delete) WHERE to_delete = FALSE;
