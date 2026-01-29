-- Update merge function to process records in batches to avoid statement timeouts
-- This version processes records in chunks using a temporary table to track batches

CREATE OR REPLACE FUNCTION merge_auctions_from_staging(
    p_auction_site VARCHAR(100),
    p_batch_size INTEGER DEFAULT 50000
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_inserted_count INTEGER := 0;
    v_updated_count INTEGER := 0;
    v_skipped_count INTEGER := 0;
    v_deleted_expired INTEGER := 0;
    v_total_staging INTEGER := 0;
    v_batch_inserted INTEGER := 0;
    v_batch_updated INTEGER := 0;
    v_batch_num INTEGER := 0;
    v_has_more BOOLEAN := true;
    v_batch_count INTEGER;
BEGIN
    -- Count records in staging
    SELECT COUNT(*) INTO v_total_staging
    FROM auctions_staging
    WHERE auction_site = p_auction_site;
    
    IF v_total_staging = 0 THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'No records found in staging table for auction_site: ' || p_auction_site
        );
    END IF;
    
    -- Process in batches to avoid statement timeouts
    -- Use a temporary table to track which records to process in each batch
    CREATE TEMP TABLE IF NOT EXISTS batch_to_process AS
    SELECT 
        domain,
        start_date,
        expiration_date,
        auction_site,
        current_bid,
        source_data,
        processed,
        preferred,
        has_statistics
    FROM auctions_staging
    WHERE auction_site = p_auction_site
    LIMIT 0;
    
    WHILE v_has_more LOOP
        v_batch_num := v_batch_num + 1;
        v_batch_inserted := 0;
        v_batch_updated := 0;
        
        -- Clear temp table and load next batch
        TRUNCATE TABLE batch_to_process;
        
        INSERT INTO batch_to_process
        SELECT 
            domain,
            start_date,
            expiration_date,
            auction_site,
            current_bid,
            source_data,
            processed,
            preferred,
            has_statistics
        FROM auctions_staging
        WHERE auction_site = p_auction_site
        ORDER BY domain, expiration_date
        LIMIT p_batch_size;
        
        GET DIAGNOSTICS v_batch_count = ROW_COUNT;
        
        IF v_batch_count = 0 THEN
            v_has_more := false;
            EXIT;
        END IF;
        
        -- Merge batch into auctions
        WITH merged AS (
            INSERT INTO auctions (
                domain,
                start_date,
                expiration_date,
                auction_site,
                current_bid,
                source_data,
                processed,
                preferred,
                has_statistics
            )
            SELECT 
                domain,
                start_date,
                expiration_date,
                auction_site,
                current_bid,
                source_data,
                processed,
                preferred,
                has_statistics
            FROM batch_to_process
            ON CONFLICT (domain, auction_site, expiration_date)
            DO UPDATE SET
                start_date = EXCLUDED.start_date,
                expiration_date = EXCLUDED.expiration_date,
                current_bid = EXCLUDED.current_bid,
                source_data = EXCLUDED.source_data,
                updated_at = NOW()
            RETURNING 
                CASE WHEN xmax = 0 THEN 'inserted' ELSE 'updated' END as action
        ),
        action_counts AS (
            SELECT 
                COUNT(*) FILTER (WHERE action = 'inserted') as inserted,
                COUNT(*) FILTER (WHERE action = 'updated') as updated
            FROM merged
        )
        SELECT 
            inserted, updated
        INTO 
            v_batch_inserted, v_batch_updated
        FROM action_counts;
        
        -- Delete processed records from staging
        DELETE FROM auctions_staging
        WHERE auction_site = p_auction_site
        AND (domain, expiration_date) IN (
            SELECT domain, expiration_date
            FROM batch_to_process
        );
        
        -- Update counters
        v_inserted_count := v_inserted_count + v_batch_inserted;
        v_updated_count := v_updated_count + v_batch_updated;
        
        -- Check if we have more records to process
        SELECT COUNT(*) > 0 INTO v_has_more
        FROM auctions_staging
        WHERE auction_site = p_auction_site;
    END LOOP;
    
    -- Drop temp table
    DROP TABLE IF EXISTS batch_to_process;
    
    -- Count skipped (if any validation issues)
    v_skipped_count := v_total_staging - v_inserted_count - v_updated_count;
    
    -- Delete expired records from auctions table (only once at the end)
    DELETE FROM auctions WHERE expiration_date < NOW();
    GET DIAGNOSTICS v_deleted_expired = ROW_COUNT;
    
    -- Cleanup: staging table should already be empty, but ensure it
    DELETE FROM auctions_staging WHERE auction_site = p_auction_site;
    
    RETURN jsonb_build_object(
        'success', true,
        'inserted', v_inserted_count,
        'updated', v_updated_count,
        'skipped', v_skipped_count,
        'deleted_expired', v_deleted_expired,
        'total_processed', v_total_staging,
        'batches_processed', v_batch_num,
        'auction_site', p_auction_site
    );
EXCEPTION WHEN OTHERS THEN
    -- Cleanup on error
    DROP TABLE IF EXISTS batch_to_process;
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_detail', PG_EXCEPTION_DETAIL,
        'total_processed', v_total_staging,
        'batches_processed', v_batch_num
    );
END;
$$;

-- Function to clear staging table in batches to avoid timeouts
CREATE OR REPLACE FUNCTION clear_auctions_staging(
    p_auction_site VARCHAR(100),
    p_batch_size INTEGER DEFAULT 10000
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_deleted_count INTEGER := 0;
    v_batch_deleted INTEGER := 0;
    v_total_deleted INTEGER := 0;
    v_has_more BOOLEAN := true;
BEGIN
    -- Delete in batches to avoid statement timeouts
    WHILE v_has_more LOOP
        -- Delete one batch
        DELETE FROM auctions_staging
        WHERE auction_site = p_auction_site
        AND ctid IN (
            SELECT ctid
            FROM auctions_staging
            WHERE auction_site = p_auction_site
            LIMIT p_batch_size
        );
        
        GET DIAGNOSTICS v_batch_deleted = ROW_COUNT;
        v_total_deleted := v_total_deleted + v_batch_deleted;
        
        -- Check if we have more records to delete
        SELECT COUNT(*) > 0 INTO v_has_more
        FROM auctions_staging
        WHERE auction_site = p_auction_site;
        
        -- Exit if no records deleted in this batch
        IF v_batch_deleted = 0 THEN
            v_has_more := false;
        END IF;
    END LOOP;
    
    RETURN jsonb_build_object(
        'success', true,
        'deleted_count', v_total_deleted,
        'auction_site', p_auction_site
    );
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_detail', PG_EXCEPTION_DETAIL,
        'deleted_count', v_total_deleted
    );
END;
$$;


















