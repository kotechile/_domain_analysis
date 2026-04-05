-- Test script for import_auctions_batch function
-- Run this in Supabase SQL Editor to verify the fix works

-- Step 1: Check current function definition (should show the old version if not updated)
-- \df+ import_auctions_batch

-- Step 2: Apply the fixed function
CREATE OR REPLACE FUNCTION import_auctions_batch(
    p_import_batch_id UUID,
    p_auction_site VARCHAR,
    p_offering_type VARCHAR DEFAULT 'auction'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_inserted INTEGER := 0;
    v_updated INTEGER := 0;
    v_deleted INTEGER := 0;
    v_new_domains INTEGER := 0;
    v_error_detail TEXT;
BEGIN
    -- UPSERT: Insert new auctions or update existing ones
    WITH upserted AS (
        INSERT INTO auctions (
            domain,
            auction_site,
            expiration_date,
            current_bid,
            link,
            offer_type,
            source_data,
            first_seen,
            last_import_batch_id,
            last_import_timestamp
        )
        SELECT DISTINCT ON (domain)
            domain,
            auction_site,
            expiration_date,
            COALESCE(current_bid, 0),
            link,
            p_offering_type,
            source_data,
            COALESCE(first_seen::timestamptz, NOW()),  -- Cast to timestamptz
            p_import_batch_id,
            NOW()
        FROM auctions_import
        WHERE import_batch_id = p_import_batch_id
        ORDER BY domain, import_timestamp DESC
        ON CONFLICT (domain, auction_site, expiration_date)
        DO UPDATE SET
            current_bid = EXCLUDED.current_bid,
            link = EXCLUDED.link,
            source_data = EXCLUDED.source_data,
            offer_type = EXCLUDED.offer_type,
            last_import_batch_id = p_import_batch_id,
            last_import_timestamp = NOW()
        RETURNING
            CASE WHEN auctions.last_import_batch_id IS NULL THEN 1 ELSE 0 END as is_new
    )
    SELECT
        COUNT(*),
        SUM(CASE WHEN is_new = 1 THEN 0 ELSE 1 END),
        SUM(is_new)
    INTO v_inserted, v_updated, v_new_domains
    FROM upserted;

    -- DELETE: Remove auctions not present in this import
    DELETE FROM auctions
    WHERE auction_site = p_auction_site
      AND offer_type = p_offering_type
      AND (last_import_batch_id IS NULL OR last_import_batch_id != p_import_batch_id);

    GET DIAGNOSTICS v_deleted = ROW_COUNT;

    -- CLEANUP: Remove processed records from staging
    DELETE FROM auctions_import
    WHERE import_batch_id = p_import_batch_id;

    RETURN jsonb_build_object(
        'success', true,
        'inserted', v_inserted,
        'updated', v_updated,
        'deleted', v_deleted,
        'new_domains', v_new_domains,
        'import_batch_id', p_import_batch_id,
        'auction_site', p_auction_site,
        'offering_type', p_offering_type
    );

EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_error_detail = PG_EXCEPTION_DETAIL;
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_detail', v_error_detail
    );
END;
$$;

-- Step 3: Test with sample data
-- First, clear any existing test data
DELETE FROM auctions_import WHERE import_batch_id = 'test-sample-import'::uuid;

-- Insert sample rows from your CSV
INSERT INTO auctions_import (domain, auction_site, expiration_date, current_bid, link, offer_type, source_data, first_seen, import_batch_id, import_timestamp)
VALUES
    ('titlepedia.com', 'namesilo', '2026-04-05 15:00:00'::timestamptz, 1, 'https://www.namesilo.com/auctions/...', 'auction', '{"Domain": "titlepedia.com", "Domain Created On": "2007-02-27 00:00:00"}'::jsonb, '2007-02-27 00:00:00', 'test-sample-import'::uuid, NOW()),
    ('skytvcard.com', 'namesilo', '2026-04-05 15:00:00'::timestamptz, 1, 'https://www.namesilo.com/auctions/...', 'auction', '{"Domain": "skytvcard.com", "Domain Created On": "2004-02-27 00:00:00"}'::jsonb, '2004-02-27 00:00:00', 'test-sample-import'::uuid, NOW()),
    ('nomadwellness.com', 'namesilo', '2026-04-05 15:00:00'::timestamptz, 330, 'https://www.namesilo.com/auctions/...', 'auction', '{"Domain": "nomadwellness.com", "Domain Created On": "2013-02-27 00:00:00"}'::jsonb, '2013-02-27 00:00:00', 'test-sample-import'::uuid, NOW());

-- Test the import function
SELECT import_auctions_batch('test-sample-import'::uuid, 'namesilo', 'auction');

-- Cleanup test data
DELETE FROM auctions WHERE last_import_batch_id = 'test-sample-import'::uuid;
DELETE FROM auctions_import WHERE import_batch_id = 'test-sample-import'::uuid;

-- If the above ran without errors, the fix works!
-- You can now redeploy the backend.
