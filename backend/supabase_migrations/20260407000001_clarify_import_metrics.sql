-- Migration: Improve import metrics and performance transparency
-- This updates the import_auctions_batch function to return clearer metrics
-- and ensures the counts are logically separate for the dashboard.

CREATE OR REPLACE FUNCTION import_auctions_batch(
    p_import_batch_id UUID,
    p_auction_site VARCHAR,
    p_offering_type VARCHAR DEFAULT 'auction'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET statement_timeout = '600s'
AS $$
DECLARE
    v_total_upserted INTEGER := 0;
    v_updated_count INTEGER := 0;
    v_new_count INTEGER := 0;
    v_deleted_count INTEGER := 0;
    v_error_detail TEXT;
    v_start_time TIMESTAMPTZ;
BEGIN
    v_start_time := clock_timestamp();

    -- UPSERT: Insert new auctions or update existing ones
    WITH staging_deduped AS (
        SELECT DISTINCT ON (domain)
            domain,
            auction_site,
            expiration_date,
            COALESCE(current_bid, 0) as current_bid,
            link,
            source_data,
            first_seen::timestamptz as first_seen
        FROM auctions_import
        WHERE import_batch_id = p_import_batch_id
        ORDER BY domain, import_timestamp DESC
    ),
    upserted AS (
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
        SELECT
            domain,
            auction_site,
            expiration_date,
            current_bid,
            link,
            p_offering_type,
            source_data,
            first_seen,
            p_import_batch_id,
            NOW()
        FROM staging_deduped
        ON CONFLICT (domain, auction_site)
        DO UPDATE SET
            expiration_date = EXCLUDED.expiration_date,
            current_bid = EXCLUDED.current_bid,
            link = EXCLUDED.link,
            source_data = EXCLUDED.source_data,
            offer_type = EXCLUDED.offer_type,
            last_import_batch_id = p_import_batch_id,
            last_import_timestamp = NOW()
        RETURNING
            (xmax = 0) as is_new
    )
    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE NOT is_new),
        COUNT(*) FILTER (WHERE is_new)
    INTO v_total_upserted, v_updated_count, v_new_count
    FROM upserted;

    -- DELETE: Remove auctions not present in this import (stale records)
    -- Only delete if they belong to this site and offering type
    DELETE FROM auctions
    WHERE auction_site = p_auction_site
      AND offer_type = p_offering_type
      AND (last_import_batch_id IS NULL OR last_import_batch_id != p_import_batch_id);

    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;

    -- CLEANUP: Remove processed records from staging
    DELETE FROM auctions_import
    WHERE import_batch_id = p_import_batch_id;

    RETURN jsonb_build_object(
        'success', true,
        'total_upserted', COALESCE(v_total_upserted, 0),
        'new_count', COALESCE(v_new_count, 0),
        'updated_count', COALESCE(v_updated_count, 0),
        'deleted_count', COALESCE(v_deleted_count, 0),
        'duration_seconds', EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time))
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
