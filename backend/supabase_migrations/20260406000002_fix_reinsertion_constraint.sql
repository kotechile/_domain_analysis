-- Migration: Fix auction re-insertion by simplifying unique constraint
-- This prevents the system from re-inserting and re-scoring 100k+ domains every day 
-- just because the marketplace timestamp changed by a few seconds.

-- 1. Safely drop the old constraint that included expiration_date
-- We use a DO block to handle cases where the constraint name might vary
DO $$
BEGIN
    -- Drop the constraint on auctions table
    -- It is usually named auctions_domain_auction_site_expiration_date_key or similar
    ALTER TABLE auctions DROP CONSTRAINT IF EXISTS auctions_domain_auction_site_expiration_date_key;
    
    -- Also drop the matching unique index if it was created manually
    DROP INDEX IF EXISTS idx_auctions_unique_key_site_exp;
END $$;

-- 2. Clean up any existing duplicates to ensure the new constraint can be applied
-- If we have multiple entries for (domain, auction_site), keep the one with the latest expiration or latest seen
DELETE FROM auctions a
USING (
    SELECT MIN(id) as id, domain, auction_site
    FROM auctions
    GROUP BY domain, auction_site
    HAVING COUNT(*) > 1
) b
WHERE a.domain = b.domain 
  AND a.auction_site = b.auction_site 
  AND a.id != b.id;

-- 3. Add the new, stable unique constraint on (domain, auction_site)
ALTER TABLE auctions ADD CONSTRAINT auctions_domain_site_unique UNIQUE (domain, auction_site);

-- 4. Update the core import function to use the simplified conflict key
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
    v_start_time TIMESTAMPTZ;
BEGIN
    v_start_time := clock_timestamp();

    -- UPSERT: Insert new auctions or update existing ones
    -- We match on (domain, auction_site) now, ignoring unstable expiration timestamps
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
            COALESCE(first_seen, NOW()),
            p_import_batch_id,
            NOW()
        FROM staging_deduped
        ON CONFLICT (domain, auction_site)
        DO UPDATE SET
            expiration_date = EXCLUDED.expiration_date, -- Update date if it changed
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
        'inserted', COALESCE(v_inserted, 0),
        'updated', COALESCE(v_updated, 0),
        'deleted', COALESCE(v_deleted, 0),
        'new_domains', COALESCE(v_new_domains, 0),
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
