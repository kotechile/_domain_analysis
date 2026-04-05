-- Atomic Auction Import Function
-- Handles: INSERT new, UPDATE existing, DELETE stale - all in one transaction
-- Preserves statistics and scores for existing records

CREATE OR REPLACE FUNCTION import_auctions_batch(
    p_import_batch_id UUID,
    p_auction_site VARCHAR,
    p_offering_type VARCHAR DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_inserted INTEGER := 0;
    v_updated INTEGER := 0;
    v_deleted INTEGER := 0;
    v_new_domains INTEGER := 0;
BEGIN
    -- =====================================================
    -- STEP 1: UPSERT - Insert new, update existing auctions
    -- =====================================================
    WITH upserted AS (
        INSERT INTO auctions (
            domain,
            auction_site,
            expiration_date,
            start_date,
            current_bid,
            link,
            offer_type,
            source_data,
            first_seen,
            last_import_batch_id,
            last_import_timestamp,
            -- Preserve these if already set, otherwise use defaults
            processed,
            preferred,
            has_statistics,
            to_delete
        )
        SELECT
            i.domain,
            i.auction_site,
            i.expiration_date,
            i.start_date,
            i.current_bid,
            i.link,
            COALESCE(i.offer_type, p_offering_type, 'auction'),
            i.source_data,
            i.first_seen,
            p_import_batch_id,
            NOW(),
            -- For new records:
            FALSE,  -- processed
            FALSE,  -- preferred
            FALSE,  -- has_statistics
            FALSE   -- to_delete
        FROM auctions_import i
        WHERE i.import_batch_id = p_import_batch_id
          AND i.auction_site = p_auction_site
        ON CONFLICT (domain, auction_site, expiration_date)
        DO UPDATE SET
            current_bid = EXCLUDED.current_bid,
            link = EXCLUDED.link,
            source_data = EXCLUDED.source_data,
            offer_type = COALESCE(EXCLUDED.offer_type, auctions.offer_type),
            first_seen = COALESCE(EXCLUDED.first_seen, auctions.first_seen),
            last_import_batch_id = p_import_batch_id,
            last_import_timestamp = NOW(),
            updated_at = NOW()
        RETURNING
            domain,
            CASE WHEN xmax = 0 THEN 'inserted' ELSE 'updated' END as action,
            CASE WHEN xmax = 0 OR score IS NULL THEN TRUE ELSE FALSE END as is_new_domain
    ),
    counts AS (
        SELECT
            COUNT(*) FILTER (WHERE action = 'inserted') as inserted_count,
            COUNT(*) FILTER (WHERE action = 'updated') as updated_count,
            COUNT(*) FILTER (WHERE is_new_domain) as new_domain_count
        FROM upserted
    )
    SELECT inserted_count, updated_count, new_domain_count
    INTO v_inserted, v_updated, v_new_domains
    FROM counts;

    -- =====================================================
    -- STEP 2: DELETE stale auctions not in this import
    -- =====================================================
    -- For GoDaddy and NameSilo: delete ALL records for site not in this import
    -- For others: delete only matching offering_type
    IF p_auction_site IN ('godaddy', 'namesilo') THEN
        -- Delete all records for this site not in current import
        DELETE FROM auctions
        WHERE auction_site = p_auction_site
          AND COALESCE(last_import_batch_id, '00000000-0000-0000-0000-000000000000'::UUID) != p_import_batch_id;

        GET DIAGNOSTICS v_deleted = ROW_COUNT;
    ELSIF p_offering_type IS NOT NULL THEN
        -- Delete only records matching offering_type
        DELETE FROM auctions
        WHERE auction_site = p_auction_site
          AND offer_type = p_offering_type
          AND COALESCE(last_import_batch_id, '00000000-0000-0000-0000-000000000000'::UUID) != p_import_batch_id;

        GET DIAGNOSTICS v_deleted = ROW_COUNT;
    ELSE
        -- Delete all records for this site
        DELETE FROM auctions
        WHERE auction_site = p_auction_site
          AND COALESCE(last_import_batch_id, '00000000-0000-0000-0000-000000000000'::UUID) != p_import_batch_id;

        GET DIAGNOSTICS v_deleted = ROW_COUNT;
    END IF;

    -- =====================================================
    -- STEP 3: Cleanup staging data
    -- =====================================================
    DELETE FROM auctions_import
    WHERE import_batch_id = p_import_batch_id;

    -- Return summary
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
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_detail', PG_EXCEPTION_DETAIL
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

-- Notify PostgREST
NOTIFY pgrst, 'reload schema';
