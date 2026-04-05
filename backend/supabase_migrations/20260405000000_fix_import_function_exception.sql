-- Migration: Fix import_auctions_batch exception handling
-- Date: 2026-04-05
-- Issue: PG_EXCEPTION_DETAIL must be retrieved via GET STACKED DIAGNOSTICS

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
    -- This preserves statistics and scores for existing auctions
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
            COALESCE(first_seen, NOW()),
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
        WHERE auctions.domain = EXCLUDED.domain
          AND auctions.auction_site = EXCLUDED.auction_site
          AND auctions.expiration_date = EXCLUDED.expiration_date
        RETURNING
            CASE WHEN auctions.last_import_batch_id IS NULL THEN 1 ELSE 0 END as is_new
    )
    SELECT
        COUNT(*),
        SUM(CASE WHEN is_new = 1 THEN 0 ELSE 1 END),
        SUM(is_new)
    INTO v_inserted, v_updated, v_new_domains
    FROM upserted;

    -- DELETE: Remove auctions not present in this import (stale data)
    -- Only delete auctions from the same auction_site and offering_type
    DELETE FROM auctions
    WHERE auction_site = p_auction_site
      AND offer_type = p_offering_type
      AND (last_import_batch_id IS NULL OR last_import_batch_id != p_import_batch_id);

    GET DIAGNOSTICS v_deleted = ROW_COUNT;

    -- CLEANUP: Remove processed records from staging
    DELETE FROM auctions_import
    WHERE import_batch_id = p_import_batch_id;

    -- Return results
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
    -- Get exception details using GET STACKED DIAGNOSTICS
    GET STACKED DIAGNOSTICS v_error_detail = PG_EXCEPTION_DETAIL;

    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_detail', v_error_detail
    );
END;
$$;

-- Add helpful comment
COMMENT ON FUNCTION import_auctions_batch IS '
Atomically imports auctions from staging table.

Flow:
1. UPSERT: Inserts new records, updates existing ones (preserves statistics/scores)
2. DELETE: Removes auctions not present in current import (stale data)
3. CLEANUP: Removes processed records from staging

Returns JSON with counts: {success, inserted, updated, deleted, new_domains}';
