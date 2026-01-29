-- Optimized scoring function for bulk processing
-- This function performs fast filtering and basic scoring in PostgreSQL
-- Complex scoring (LFS, semantic) is handled by Python backend

CREATE OR REPLACE FUNCTION filter_and_pre_score_auctions(
    p_batch_limit INTEGER DEFAULT 10000,
    p_config_id UUID DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    domain VARCHAR(255),
    source_data JSONB,
    age_score DECIMAL(10,2),
    passed_filter BOOLEAN,
    filter_reason TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_config RECORD;
    v_tier_1_tlds TEXT[];
    v_max_domain_length INTEGER;
    v_max_numbers INTEGER;
BEGIN
    -- Get active config (or use provided config_id)
    IF p_config_id IS NULL THEN
        SELECT * INTO v_config
        FROM scoring_config
        WHERE is_active = TRUE
        ORDER BY created_at DESC
        LIMIT 1;
    ELSE
        SELECT * INTO v_config
        FROM scoring_config
        WHERE id = p_config_id;
    END IF;

    IF v_config IS NULL THEN
        RAISE EXCEPTION 'No active scoring configuration found';
    END IF;

    -- Extract config values
    v_tier_1_tlds := v_config.tier_1_tlds;
    v_max_domain_length := v_config.max_domain_length;
    v_max_numbers := v_config.max_numbers;

    -- Return filtered and pre-scored records
    RETURN QUERY
    SELECT 
        a.id,
        a.domain,
        a.source_data,
        -- Age score calculation (fast, database-level)
        CASE 
            WHEN a.source_data->>'registered_date' IS NOT NULL THEN
                CASE 
                    WHEN EXTRACT(YEAR FROM AGE(NOW(), (a.source_data->>'registered_date')::TIMESTAMP)) >= 10 THEN 100.0
                    WHEN EXTRACT(YEAR FROM AGE(NOW(), (a.source_data->>'registered_date')::TIMESTAMP)) >= 5 THEN 50.0
                    ELSE 20.0
                END
            ELSE 0.0
        END AS age_score,
        -- Filter check
        CASE 
            -- Check TLD
            WHEN '.' || LOWER(SPLIT_PART(a.domain, '.', -1)) = ANY(v_tier_1_tlds) AND
                 -- Check length
                 LENGTH(SPLIT_PART(a.domain, '.', 1)) <= v_max_domain_length AND
                 -- Check for hyphens or special characters
                 SPLIT_PART(a.domain, '.', 1) !~ '[^a-zA-Z0-9]' AND
                 -- Check number count
                 (LENGTH(SPLIT_PART(a.domain, '.', 1)) - LENGTH(REGEXP_REPLACE(SPLIT_PART(a.domain, '.', 1), '[0-9]', '', 'g'))) <= v_max_numbers
            THEN TRUE
            ELSE FALSE
        END AS passed_filter,
        -- Filter reason
        CASE 
            WHEN '.' || LOWER(SPLIT_PART(a.domain, '.', -1)) != ANY(v_tier_1_tlds) THEN 'TLD not in whitelist'
            WHEN LENGTH(SPLIT_PART(a.domain, '.', 1)) > v_max_domain_length THEN 'Domain name exceeds max length'
            WHEN SPLIT_PART(a.domain, '.', 1) ~ '[^a-zA-Z0-9]' THEN 'Contains hyphens or special characters'
            WHEN (LENGTH(SPLIT_PART(a.domain, '.', 1)) - LENGTH(REGEXP_REPLACE(SPLIT_PART(a.domain, '.', 1), '[0-9]', '', 'g'))) > v_max_numbers THEN 'Contains too many numbers'
            ELSE NULL
        END AS filter_reason
    FROM auctions a
    WHERE a.processed = FALSE
    ORDER BY a.created_at ASC  -- Process oldest first
    LIMIT p_batch_limit;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION filter_and_pre_score_auctions(INTEGER, UUID) TO service_role;
GRANT EXECUTE ON FUNCTION filter_and_pre_score_auctions(INTEGER, UUID) TO authenticated;

-- Add comment
COMMENT ON FUNCTION filter_and_pre_score_auctions IS 'Fast filtering and pre-scoring function. Returns unprocessed records with age scores and filter status for Python backend processing.';

-- Create function to bulk update scores
CREATE OR REPLACE FUNCTION bulk_update_auction_scores(
    p_scores JSONB  -- Format: {"domain_id": {"score": 85.5, "lfs_score": 75.0, "sv_score": 80.0}, ...}
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_updated_count INTEGER := 0;
    v_domain_id UUID;
    v_score DECIMAL(10,2);
    v_lfs_score DECIMAL(10,2);
    v_sv_score DECIMAL(10,2);
    v_score_item JSONB;
BEGIN
    -- Update scores for each domain in the JSONB object
    FOR v_domain_id, v_score_item IN SELECT * FROM jsonb_each(p_scores)
    LOOP
        -- Handle NULL scores (for records that failed filtering)
        IF v_score_item->>'score' IS NULL OR v_score_item->>'score' = 'null' THEN
            v_score := NULL;
        ELSE
            v_score := (v_score_item->>'score')::DECIMAL;
        END IF;
        
        -- LFS and SV scores can also be NULL
        IF v_score_item->>'lfs_score' IS NULL OR v_score_item->>'lfs_score' = 'null' THEN
            v_lfs_score := NULL;
        ELSE
            v_lfs_score := (v_score_item->>'lfs_score')::DECIMAL;
        END IF;
        
        IF v_score_item->>'sv_score' IS NULL OR v_score_item->>'sv_score' = 'null' THEN
            v_sv_score := NULL;
        ELSE
            v_sv_score := (v_score_item->>'sv_score')::DECIMAL;
        END IF;
        
        UPDATE auctions
        SET 
            score = v_score,
            processed = TRUE,
            updated_at = NOW()
        WHERE id = (v_domain_id::TEXT)::UUID
        AND processed = FALSE;
        
        IF FOUND THEN
            v_updated_count := v_updated_count + 1;
        END IF;
    END LOOP;
    
    -- Return statistics
    RETURN jsonb_build_object(
        'success', TRUE,
        'updated_count', v_updated_count
    );
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION bulk_update_auction_scores(JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION bulk_update_auction_scores(JSONB) TO authenticated;

-- Add comment
COMMENT ON FUNCTION bulk_update_auction_scores IS 'Bulk update auction scores from Python backend. Marks records as processed.';

-- Create function to recalculate rankings globally
-- Note: For large datasets (100K+ records), this may timeout. 
-- Consider running this separately or increasing statement_timeout.
CREATE OR REPLACE FUNCTION recalculate_auction_rankings()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_ranked_count INTEGER := 0;
    v_preferred_count INTEGER := 0;
BEGIN
    -- Recalculate rankings using window function
    -- This is optimized with indexes on score and ranking columns
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
    AND a.ranking IS DISTINCT FROM ra.ranking;

    GET DIAGNOSTICS v_ranked_count = ROW_COUNT;
    
    -- Update preferred flag based on active config
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
    
    -- Return statistics
    RETURN jsonb_build_object(
        'success', TRUE,
        'ranked_count', v_ranked_count
    );
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION recalculate_auction_rankings() TO service_role;
GRANT EXECUTE ON FUNCTION recalculate_auction_rankings() TO authenticated;

-- Add comment
COMMENT ON FUNCTION recalculate_auction_rankings IS 'Recalculate global rankings and preferred flags for all scored auctions.';

-- Create additional indexes for performance
CREATE INDEX IF NOT EXISTS idx_auctions_processed_created ON auctions(processed, created_at) WHERE processed = FALSE;
CREATE INDEX IF NOT EXISTS idx_auctions_domain_tld ON auctions((SPLIT_PART(domain, '.', -1))) WHERE processed = FALSE;
CREATE INDEX IF NOT EXISTS idx_auctions_source_data_registered ON auctions USING GIN ((source_data->'registered_date')) WHERE processed = FALSE;


















