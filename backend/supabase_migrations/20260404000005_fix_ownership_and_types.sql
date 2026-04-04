-- Migration: Definitive fix for "must be owner of table auctions"
-- Problem: ALTER TABLE ... DISABLE TRIGGER requires table ownership.
-- Fix: Add SECURITY DEFINER to merge and cleanup functions so they run as the owner (postgres).
-- Also ensures type consistency (TEXT) and explicit casting.

DO $$
DECLARE
    r RECORD;
BEGIN
    -- 1. Drop ALL versions of the functions to avoid ambiguity (42725)
    FOR r IN (SELECT oid::regprocedure as sig FROM pg_proc WHERE proname = 'merge_auctions_delta_from_staging') LOOP
        EXECUTE 'DROP FUNCTION ' || r.sig;
    END LOOP;
    
    FOR r IN (SELECT oid::regprocedure as sig FROM pg_proc WHERE proname = 'cleanup_stuck_upload') LOOP
        EXECUTE 'DROP FUNCTION ' || r.sig;
    END LOOP;
END $$;

-- ============================================================
-- merge_auctions_delta_from_staging
-- ============================================================
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
SET statement_timeout = '360s'
AS $$
DECLARE 
    v_staging_table TEXT; 
    v_deleted_count INTEGER := 0;
    v_job_id_uuid UUID;
BEGIN
    -- Safe UUID cast
    BEGIN
        v_job_id_uuid := p_job_id::UUID;
    EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION 'Invalid job_id format: %', p_job_id;
    END;

    v_staging_table := CASE WHEN p_staging_table_suffix IS NOT NULL THEN 'auctions_staging_' || p_staging_table_suffix ELSE 'auctions_staging' END;
    
    -- IMPORTANT: This requires table ownership, which SECURITY DEFINER provides
    ALTER TABLE auctions DISABLE TRIGGER update_auctions_updated_at;
    
    -- Step 1: Mark stale records
    IF p_offering_type IS NOT NULL AND p_auction_site NOT IN ('godaddy', 'namesilo') THEN
        UPDATE auctions SET to_delete = TRUE 
        WHERE auctions.auction_site = p_auction_site 
          AND (auctions.offer_type = p_offering_type OR (auctions.offer_type IS NULL AND p_offering_type IS NULL)) 
          AND auctions.to_delete = FALSE;
    ELSE
        UPDATE auctions SET to_delete = TRUE 
        WHERE auctions.auction_site = p_auction_site AND auctions.to_delete = FALSE;
    END IF;
    
    GET DIAGNOSTICS v_deleted_count := ROW_COUNT;
    ALTER TABLE auctions ENABLE TRIGGER update_auctions_updated_at;
    
    -- Step 2: Merge from staging
    RETURN QUERY EXECUTE format(
        'INSERT INTO auctions (domain, auction_site, expiration_date, start_date, current_bid, link, offer_type, source_data, first_seen, to_delete, score, processed, preferred, has_statistics, updated_at)
         SELECT s.domain::TEXT, s.auction_site::TEXT, s.expiration_date, s.start_date, s.current_bid, s.link::TEXT, s.offer_type::TEXT, s.source_data, s.first_seen, FALSE, s.score, FALSE, FALSE, FALSE, NOW()
         FROM %I s WHERE s.job_id = %L
         ON CONFLICT (domain, auction_site, expiration_date) DO UPDATE
         SET start_date = EXCLUDED.start_date, current_bid = EXCLUDED.current_bid, link = EXCLUDED.link::TEXT, offer_type = EXCLUDED.offer_type::TEXT, source_data = EXCLUDED.source_data, to_delete = FALSE, updated_at = NOW()
         RETURNING domain::TEXT, auction_site::TEXT, expiration_date, start_date, current_bid, link::TEXT, offer_type::TEXT, source_data, first_seen, (xmax = 0)::BOOLEAN',
        v_staging_table, v_job_id_uuid
    );
    
    -- Step 3: Cleanup staging
    EXECUTE format('DELETE FROM %I WHERE job_id = %L', v_staging_table, v_job_id_uuid);
END;
$$;

-- ============================================================
-- cleanup_stuck_upload
-- ============================================================
CREATE OR REPLACE FUNCTION cleanup_stuck_upload(p_job_id VARCHAR)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_auction_site VARCHAR; v_offering_type VARCHAR; v_deleted_auctions INTEGER := 0; v_deleted_staging INTEGER := 0; v_cleaned_staging_tables TEXT[] := ARRAY[]::TEXT[]; v_job_id_uuid UUID;
BEGIN
    BEGIN v_job_id_uuid := p_job_id::UUID; EXCEPTION WHEN OTHERS THEN RETURN jsonb_build_object('success', false, 'error', 'Invalid job_id format: ' || p_job_id); END;
    
    SELECT auction_site, offering_type INTO v_auction_site, v_offering_type FROM csv_upload_progress WHERE job_id = p_job_id;
    IF v_auction_site IS NULL THEN RETURN jsonb_build_object('success', false, 'error', 'Job not found'); END IF;
    
    ALTER TABLE auctions DISABLE TRIGGER update_auctions_updated_at;
    
    IF v_offering_type IS NOT NULL AND v_auction_site NOT IN ('godaddy', 'namesilo') THEN
        DELETE FROM auctions WHERE auction_site = v_auction_site AND (offer_type = v_offering_type OR (offer_type IS NULL AND v_offering_type IS NULL)) AND to_delete = TRUE;
    ELSE
        DELETE FROM auctions WHERE auction_site = v_auction_site AND to_delete = TRUE;
    END IF;
    
    GET DIAGNOSTICS v_deleted_auctions := ROW_COUNT;
    ALTER TABLE auctions ENABLE TRIGGER update_auctions_updated_at;
    
    FOR i IN 0..4 LOOP
        EXECUTE format('DELETE FROM auctions_staging_%s WHERE job_id = %L', i, v_job_id_uuid);
        GET DIAGNOSTICS v_deleted_staging := ROW_COUNT;
        IF v_deleted_staging > 0 THEN v_cleaned_staging_tables := array_append(v_cleaned_staging_tables, format('auctions_staging_%s: %s', i, v_deleted_staging)); END IF;
    END LOOP;
    
    DELETE FROM auctions_staging WHERE job_id = v_job_id_uuid;
    
    UPDATE csv_upload_progress SET status = 'pending', current_stage = 'ready', error_message = NULL, processed_records = 0, inserted_count = 0, updated_count = 0, skipped_count = 0, deleted_expired_count = 0, progress_percentage = '0.00', completed_at = NULL, updated_at = NOW() WHERE job_id = p_job_id;
    
    RETURN jsonb_build_object('success', true, 'job_id', p_job_id, 'auction_site', v_auction_site, 'deleted_auctions', v_deleted_auctions, 'cleaned_staging', v_cleaned_staging_tables);
END;
$$;

-- Grants
GRANT EXECUTE ON FUNCTION merge_auctions_delta_from_staging TO service_role;
GRANT EXECUTE ON FUNCTION merge_auctions_delta_from_staging TO authenticated;
GRANT EXECUTE ON FUNCTION merge_auctions_delta_from_staging TO anon;

GRANT EXECUTE ON FUNCTION cleanup_stuck_upload TO service_role;
GRANT EXECUTE ON FUNCTION cleanup_stuck_upload TO authenticated;
GRANT EXECUTE ON FUNCTION cleanup_stuck_upload TO anon;
