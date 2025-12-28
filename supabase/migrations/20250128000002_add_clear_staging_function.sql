-- Function to clear staging table efficiently
-- Tries a simple DELETE first (fast for normal cases), falls back to batching if needed

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
    v_record_count INTEGER := 0;
BEGIN
    -- First, try a simple DELETE (most efficient for normal cases)
    -- This will be fast if there are few records or if the table is empty
    BEGIN
        DELETE FROM auctions_staging
        WHERE auction_site = p_auction_site;
        
        GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
        
        -- If successful, return immediately
        RETURN jsonb_build_object(
            'success', true,
            'deleted_count', v_deleted_count,
            'auction_site', p_auction_site,
            'method', 'simple_delete'
        );
    EXCEPTION WHEN OTHERS THEN
        -- If simple delete times out (likely due to many leftover records),
        -- fall back to batched deletion
        IF SQLSTATE = '57014' THEN  -- Statement timeout
            -- Count remaining records
            SELECT COUNT(*) INTO v_record_count
            FROM auctions_staging
            WHERE auction_site = p_auction_site;
            
            -- Delete in batches to avoid timeouts
            WHILE v_has_more LOOP
                -- Delete one batch using ctid (physical row identifier)
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
                'auction_site', p_auction_site,
                'method', 'batched_delete',
                'initial_count', v_record_count
            );
        ELSE
            -- Re-raise other exceptions
            RAISE;
        END IF;
    END;
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_detail', PG_EXCEPTION_DETAIL,
        'deleted_count', v_total_deleted
    );
END;
$$;









