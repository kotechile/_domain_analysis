-- Chunked ranking recalculation function for very large datasets
-- This processes rankings in batches to avoid timeouts

CREATE OR REPLACE FUNCTION recalculate_auction_rankings_chunked(
    p_batch_size INTEGER DEFAULT 50000
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_total_ranked INTEGER := 0;
    v_total_preferred INTEGER := 0;
    v_batch_ranked INTEGER := 0;
    v_batch_preferred INTEGER := 0;
    v_processed_count INTEGER := 0;
    v_start_time TIMESTAMP;
    v_end_time TIMESTAMP;
    v_min_score DECIMAL(10,2);
    v_max_score DECIMAL(10,2);
BEGIN
    v_start_time := clock_timestamp();
    
    -- Get score range
    SELECT MIN(score), MAX(score) INTO v_min_score, v_max_score
    FROM auctions
    WHERE score IS NOT NULL;
    
    IF v_min_score IS NULL THEN
        RETURN jsonb_build_object(
            'success', TRUE,
            'ranked_count', 0,
            'preferred_count', 0,
            'message', 'No scored records found'
        );
    END IF;
    
    -- Process in chunks by score ranges
    -- This avoids loading all records into memory at once
    LOOP
        -- Calculate rankings for a batch of records
        WITH scored_batch AS (
            SELECT id, score
            FROM auctions
            WHERE score IS NOT NULL
            AND (ranking IS NULL OR ranking = 0)  -- Only process unranked records
            ORDER BY score DESC
            LIMIT p_batch_size
        ),
        ranked_batch AS (
            SELECT 
                id,
                ROW_NUMBER() OVER (
                    ORDER BY score DESC
                ) + v_total_ranked AS ranking
            FROM scored_batch
        )
        UPDATE auctions a
        SET 
            ranking = rb.ranking,
            updated_at = NOW()
        FROM ranked_batch rb
        WHERE a.id = rb.id;
        
        GET DIAGNOSTICS v_batch_ranked = ROW_COUNT;
        v_total_ranked := v_total_ranked + v_batch_ranked;
        v_processed_count := v_processed_count + 1;
        
        -- Exit if no more records to process
        EXIT WHEN v_batch_ranked = 0;
        
        -- Safety check to avoid infinite loops
        IF v_processed_count > 100 THEN
            RAISE WARNING 'Processed 100 batches, stopping to avoid infinite loop';
            EXIT;
        END IF;
    END LOOP;
    
    -- Now recalculate all rankings properly using window function
    -- But only update records that need updating
    WITH all_ranked AS (
        SELECT 
            id,
            ROW_NUMBER() OVER (ORDER BY score DESC NULLS LAST) AS new_ranking
        FROM auctions
        WHERE score IS NOT NULL
    )
    UPDATE auctions a
    SET 
        ranking = ar.new_ranking,
        updated_at = NOW()
    FROM all_ranked ar
    WHERE a.id = ar.id
    AND (a.ranking IS NULL OR a.ranking IS DISTINCT FROM ar.new_ranking);
    
    GET DIAGNOSTICS v_total_ranked = ROW_COUNT;
    
    -- Update preferred flags
    WITH config AS (
        SELECT 
            score_threshold,
            rank_threshold,
            use_both_thresholds
        FROM scoring_config
        WHERE is_active = TRUE
        ORDER BY created_at DESC
        LIMIT 1
    )
    UPDATE auctions a
    SET 
        preferred = CASE 
            WHEN c.score_threshold IS NULL AND c.rank_threshold IS NULL THEN TRUE
            WHEN c.use_both_thresholds THEN
                (c.score_threshold IS NULL OR a.score >= c.score_threshold) AND
                (c.rank_threshold IS NULL OR a.ranking <= c.rank_threshold)
            ELSE
                (c.score_threshold IS NULL OR a.score >= c.score_threshold) OR
                (c.rank_threshold IS NULL OR a.ranking <= c.rank_threshold)
        END,
        updated_at = NOW()
    FROM config c
    WHERE a.score IS NOT NULL
    AND a.ranking IS NOT NULL;
    
    GET DIAGNOSTICS v_total_preferred = ROW_COUNT;
    
    v_end_time := clock_timestamp();
    
    RETURN jsonb_build_object(
        'success', TRUE,
        'ranked_count', v_total_ranked,
        'preferred_count', v_total_preferred,
        'execution_time_seconds', EXTRACT(EPOCH FROM (v_end_time - v_start_time)),
        'batches_processed', v_processed_count
    );
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION recalculate_auction_rankings_chunked(INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION recalculate_auction_rankings_chunked(INTEGER) TO authenticated;

-- Add comment
COMMENT ON FUNCTION recalculate_auction_rankings_chunked IS 'Chunked ranking recalculation for very large datasets. Processes in batches to avoid timeouts.';














