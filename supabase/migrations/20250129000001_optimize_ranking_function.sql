-- Optimize ranking recalculation for large datasets
-- This version uses a more efficient approach that should handle 100K+ records

CREATE OR REPLACE FUNCTION recalculate_auction_rankings()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_ranked_count INTEGER := 0;
    v_preferred_count INTEGER := 0;
    v_start_time TIMESTAMP;
    v_end_time TIMESTAMP;
BEGIN
    v_start_time := clock_timestamp();
    
    -- Step 1: Recalculate rankings using window function
    -- This is optimized with indexes on score column
    WITH ranked_auctions AS (
        SELECT 
            id,
            ROW_NUMBER() OVER (ORDER BY score DESC NULLS LAST) AS ranking
        FROM auctions
        WHERE score IS NOT NULL
    )
    UPDATE auctions a
    SET 
        ranking = ra.ranking,
        updated_at = NOW()
    FROM ranked_auctions ra
    WHERE a.id = ra.id
    AND (a.ranking IS NULL OR a.ranking IS DISTINCT FROM ra.ranking);

    GET DIAGNOSTICS v_ranked_count = ROW_COUNT;
    
    -- Step 2: Update preferred flag based on active config
    -- This is done separately to avoid complex joins
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
    AND a.ranking IS NOT NULL
    AND (a.preferred IS NULL OR a.preferred IS DISTINCT FROM 
        CASE 
            WHEN c.score_threshold IS NULL AND c.rank_threshold IS NULL THEN TRUE
            WHEN c.use_both_thresholds THEN
                (c.score_threshold IS NULL OR a.score >= c.score_threshold) AND
                (c.rank_threshold IS NULL OR a.ranking <= c.rank_threshold)
            ELSE
                (c.score_threshold IS NULL OR a.score >= c.score_threshold) OR
                (c.rank_threshold IS NULL OR a.ranking <= c.rank_threshold)
        END);

    GET DIAGNOSTICS v_preferred_count = ROW_COUNT;
    
    v_end_time := clock_timestamp();
    
    -- Return statistics
    RETURN jsonb_build_object(
        'success', TRUE,
        'ranked_count', v_ranked_count,
        'preferred_count', v_preferred_count,
        'execution_time_seconds', EXTRACT(EPOCH FROM (v_end_time - v_start_time))
    );
END;
$$;

-- Add comment
COMMENT ON FUNCTION recalculate_auction_rankings IS 'Recalculate global rankings and preferred flags for all scored auctions. Optimized for large datasets (100K+ records).';

-- Ensure we have the right indexes for performance
CREATE INDEX IF NOT EXISTS idx_auctions_score_desc ON auctions(score DESC NULLS LAST) WHERE score IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_auctions_ranking_score ON auctions(ranking, score) WHERE ranking IS NOT NULL AND score IS NOT NULL;


















