-- Create function for scoring auctions
-- This function performs filtering, scoring, ranking, and preferred flag updates
-- LFS and semantic scores are provided by N8N Python node

CREATE OR REPLACE FUNCTION score_and_rank_auctions(
    p_config_id UUID DEFAULT NULL,
    p_batch_limit INTEGER DEFAULT 10000,
    p_lfs_scores JSONB DEFAULT NULL,
    p_semantic_scores JSONB DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_config RECORD;
    v_processed_count INTEGER := 0;
    v_preferred_count INTEGER := 0;
    v_ranked_count INTEGER := 0;
    v_age_weight DECIMAL(3,2);
    v_lfs_weight DECIMAL(3,2);
    v_sv_weight DECIMAL(3,2);
    v_score_threshold DECIMAL(5,2);
    v_rank_threshold INTEGER;
    v_use_both_thresholds BOOLEAN;
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
    v_age_weight := v_config.age_weight;
    v_lfs_weight := v_config.lfs_weight;
    v_sv_weight := v_config.sv_weight;
    v_score_threshold := v_config.score_threshold;
    v_rank_threshold := v_config.rank_threshold;
    v_use_both_thresholds := v_config.use_both_thresholds;

    -- Stage 1: Filter and score auctions
    -- Update auctions with scores for domains that pass filtering
    WITH scored_auctions AS (
        SELECT 
            a.id,
            a.domain,
            a.source_data,
            -- Stage 1 Filtering checks
            CASE 
                -- Check TLD (extract TLD with dot)
                WHEN '.' || LOWER(SPLIT_PART(a.domain, '.', -1)) NOT IN (
                    SELECT UNNEST(v_config.tier_1_tlds)
                ) THEN NULL
                -- Check length (domain name without TLD)
                WHEN LENGTH(SPLIT_PART(a.domain, '.', 1)) > v_config.max_domain_length THEN NULL
                -- Check for hyphens or special characters
                WHEN SPLIT_PART(a.domain, '.', 1) ~ '[^a-zA-Z0-9]' THEN NULL
                -- Check number count
                WHEN (LENGTH(SPLIT_PART(a.domain, '.', 1)) - LENGTH(REGEXP_REPLACE(SPLIT_PART(a.domain, '.', 1), '[0-9]', '', 'g'))) > v_config.max_numbers THEN NULL
                ELSE 1
            END AS passed_filter,
            -- Age score calculation
            CASE 
                WHEN a.source_data->>'registered_date' IS NOT NULL THEN
                    CASE 
                        WHEN EXTRACT(YEAR FROM AGE(NOW(), (a.source_data->>'registered_date')::TIMESTAMP)) >= 10 THEN 100.0
                        WHEN EXTRACT(YEAR FROM AGE(NOW(), (a.source_data->>'registered_date')::TIMESTAMP)) >= 5 THEN 50.0
                        ELSE 20.0
                    END
                ELSE 0.0
            END AS age_score,
            -- Lexical frequency score (from N8N if provided)
            CASE 
                WHEN p_lfs_scores IS NOT NULL AND p_lfs_scores ? a.domain THEN
                    (p_lfs_scores->>a.domain)::DECIMAL
                ELSE 0.0
            END AS lfs_score,
            -- Semantic value score (from N8N if provided)
            CASE 
                WHEN p_semantic_scores IS NOT NULL AND p_semantic_scores ? a.domain THEN
                    (p_semantic_scores->>a.domain)::DECIMAL
                ELSE 0.0
            END AS sv_score
        FROM auctions a
        WHERE a.processed = FALSE
        LIMIT p_batch_limit
    ),
    calculated_scores AS (
        SELECT 
            id,
            domain,
            CASE 
                WHEN passed_filter IS NULL THEN NULL
                ELSE ROUND(
                    (age_score * v_age_weight) + 
                    (lfs_score * v_lfs_weight) + 
                    (sv_score * v_sv_weight),
                    2
                )
            END AS total_score
        FROM scored_auctions
    )
    UPDATE auctions a
    SET 
        score = cs.total_score,
        processed = TRUE,
        updated_at = NOW()
    FROM calculated_scores cs
    WHERE a.id = cs.id;

    GET DIAGNOSTICS v_processed_count = ROW_COUNT;

    -- Stage 2: Calculate rankings using window function
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

    -- Stage 3: Update preferred flag based on thresholds
    UPDATE auctions
    SET 
        preferred = CASE 
            WHEN v_score_threshold IS NULL AND v_rank_threshold IS NULL THEN TRUE
            WHEN v_use_both_thresholds THEN
                (v_score_threshold IS NULL OR score >= v_score_threshold) AND
                (v_rank_threshold IS NULL OR ranking <= v_rank_threshold)
            ELSE
                (v_score_threshold IS NULL OR score >= v_score_threshold) OR
                (v_rank_threshold IS NULL OR ranking <= v_rank_threshold)
        END,
        updated_at = NOW()
    WHERE score IS NOT NULL
    AND ranking IS NOT NULL;

    GET DIAGNOSTICS v_preferred_count = ROW_COUNT;

    -- Return statistics
    RETURN jsonb_build_object(
        'success', TRUE,
        'processed_count', v_processed_count,
        'ranked_count', v_ranked_count,
        'preferred_count', v_preferred_count,
        'config_id', v_config.id,
        'config_name', v_config.name
    );
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION score_and_rank_auctions(UUID, INTEGER, JSONB, JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION score_and_rank_auctions(UUID, INTEGER, JSONB, JSONB) TO authenticated;

-- Add comment
COMMENT ON FUNCTION score_and_rank_auctions IS 'Scores, ranks, and marks preferred auctions. LFS and semantic scores provided by N8N Python node.';
