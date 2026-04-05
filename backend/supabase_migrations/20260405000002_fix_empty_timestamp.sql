-- Migration: Fix import_auctions_batch to handle empty strings in first_seen
-- Date: 2026-04-05
-- Issue: Empty strings can't be cast to timestamptz

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
    v_inserted INTEGER := 0;
    v_updated INTEGER := 0;
    v_deleted INTEGER := 0;
    v_new_domains INTEGER := 0;
    v_error_detail TEXT;
BEGIN
    -- UPSERT: Insert new auctions or update existing ones
    WITH staging_deduped AS (
        SELECT DISTINCT ON (domain)
            domain,
            auction_site,
            expiration_date,
            COALESCE(current_bid, 0) as current_bid,
            link,
            source_data,
            -- Handle empty strings and NULLs for first_seen
            CASE
                WHEN first_seen IS NULL THEN NULL
                WHEN first_seen = '' THEN NULL
                WHEN TRIM(first_seen) = '' THEN NULL
                ELSE first_seen::timestamptz
            END as first_seen
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
            COALESCE(first_seen, NOW()),
            p_import_batch_id,
            NOW()
        FROM staging_deduped
        ON CONFLICT (domain, auction_site, expiration_date)
        DO UPDATE SET
            current_bid = EXCLUDED.current_bid,
            link = EXCLUDED.link,
            source_data = EXCLUDED.source_data,
            offer_type = EXCLUDED.offer_type,
            last_import_batch_id = p_import_batch_id,
            last_import_timestamp = NOW()
        RETURNING
            CASE WHEN xmax::text::int = 0 THEN 1 ELSE 0 END as is_new
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
        'new_domains', v_new_domains
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
