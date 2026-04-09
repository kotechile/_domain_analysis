-- Stepwise ranking recalculation for large auction datasets.
-- Each invocation updates only a single slice of rows so callers can iterate
-- safely without holding one long-running SQL statement open.

CREATE INDEX IF NOT EXISTS idx_auctions_score_desc_id
ON auctions (score DESC, id)
WHERE score IS NOT NULL;

CREATE OR REPLACE FUNCTION recalculate_auction_rankings_step(
    p_batch_size INTEGER DEFAULT 5000,
    p_start_rank INTEGER DEFAULT 1,
    p_after_score DECIMAL(10,2) DEFAULT NULL,
    p_after_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_processed_count INTEGER := 0;
    v_ranking_updates INTEGER := 0;
    v_preferred_updates INTEGER := 0;
    v_total_scored INTEGER := 0;
    v_next_start_rank INTEGER := p_start_rank;
    v_last_score DECIMAL(10,2);
    v_last_id UUID;
    v_score_threshold DECIMAL(10,2);
    v_rank_threshold INTEGER;
    v_use_both_thresholds BOOLEAN;
BEGIN
    IF p_batch_size IS NULL OR p_batch_size <= 0 THEN
        p_batch_size := 5000;
    END IF;

    IF p_start_rank IS NULL OR p_start_rank <= 0 THEN
        p_start_rank := 1;
    END IF;

    SELECT COUNT(*)
    INTO v_total_scored
    FROM auctions
    WHERE score IS NOT NULL;

    IF v_total_scored = 0 THEN
        RETURN jsonb_build_object(
            'success', TRUE,
            'processed_count', 0,
            'ranking_updates', 0,
            'preferred_updates', 0,
            'next_start_rank', p_start_rank,
            'next_after_score', NULL,
            'next_after_id', NULL,
            'total_scored', 0,
            'done', TRUE,
            'message', 'No scored records found'
        );
    END IF;

    CREATE TEMP TABLE tmp_ranking_batch ON COMMIT DROP AS
    SELECT
        id,
        score,
        ROW_NUMBER() OVER (ORDER BY score DESC, id ASC) + p_start_rank - 1 AS new_ranking
    FROM (
        SELECT id, score
        FROM auctions
        WHERE score IS NOT NULL
        AND (
            p_after_score IS NULL
            OR score < p_after_score
            OR (score = p_after_score AND id > p_after_id)
        )
        ORDER BY score DESC, id ASC
        LIMIT p_batch_size
    ) batch;

    SELECT COUNT(*)
    INTO v_processed_count
    FROM tmp_ranking_batch;

    IF v_processed_count = 0 THEN
        RETURN jsonb_build_object(
            'success', TRUE,
            'processed_count', 0,
            'ranking_updates', 0,
            'preferred_updates', 0,
            'next_start_rank', p_start_rank,
            'next_after_score', p_after_score,
            'next_after_id', p_after_id,
            'total_scored', v_total_scored,
            'done', TRUE,
            'message', 'No additional ranked rows to process'
        );
    END IF;

    UPDATE auctions a
    SET
        ranking = t.new_ranking,
        name_rank = t.new_ranking,
        updated_at = NOW()
    FROM tmp_ranking_batch t
    WHERE a.id = t.id
    AND (a.ranking IS NULL OR a.ranking IS DISTINCT FROM t.new_ranking);

    GET DIAGNOSTICS v_ranking_updates = ROW_COUNT;

    SELECT
        score_threshold,
        rank_threshold,
        use_both_thresholds
    INTO
        v_score_threshold,
        v_rank_threshold,
        v_use_both_thresholds
    FROM scoring_config
    WHERE is_active = TRUE
    ORDER BY created_at DESC
    LIMIT 1;

    IF FOUND THEN
        UPDATE auctions a
        SET
            preferred = CASE
                WHEN v_score_threshold IS NULL AND v_rank_threshold IS NULL THEN TRUE
                WHEN v_use_both_thresholds THEN
                    (v_score_threshold IS NULL OR a.score >= v_score_threshold) AND
                    (v_rank_threshold IS NULL OR t.new_ranking <= v_rank_threshold)
                ELSE
                    (v_score_threshold IS NULL OR a.score >= v_score_threshold) OR
                    (v_rank_threshold IS NULL OR t.new_ranking <= v_rank_threshold)
            END,
            name_preferred = CASE
                WHEN v_score_threshold IS NULL AND v_rank_threshold IS NULL THEN TRUE
                WHEN v_use_both_thresholds THEN
                    (v_score_threshold IS NULL OR a.score >= v_score_threshold) AND
                    (v_rank_threshold IS NULL OR t.new_ranking <= v_rank_threshold)
                ELSE
                    (v_score_threshold IS NULL OR a.score >= v_score_threshold) OR
                    (v_rank_threshold IS NULL OR t.new_ranking <= v_rank_threshold)
            END,
            updated_at = NOW()
        FROM tmp_ranking_batch t
        WHERE a.id = t.id
        AND (
            a.preferred IS NULL
            OR a.preferred IS DISTINCT FROM
                CASE
                    WHEN v_score_threshold IS NULL AND v_rank_threshold IS NULL THEN TRUE
                    WHEN v_use_both_thresholds THEN
                        (v_score_threshold IS NULL OR a.score >= v_score_threshold) AND
                        (v_rank_threshold IS NULL OR t.new_ranking <= v_rank_threshold)
                    ELSE
                        (v_score_threshold IS NULL OR a.score >= v_score_threshold) OR
                        (v_rank_threshold IS NULL OR t.new_ranking <= v_rank_threshold)
                END
        );

        GET DIAGNOSTICS v_preferred_updates = ROW_COUNT;
    END IF;

    SELECT score, id, new_ranking
    INTO v_last_score, v_last_id, v_next_start_rank
    FROM tmp_ranking_batch
    ORDER BY new_ranking DESC
    LIMIT 1;

    v_next_start_rank := v_next_start_rank + 1;

    RETURN jsonb_build_object(
        'success', TRUE,
        'processed_count', v_processed_count,
        'ranking_updates', v_ranking_updates,
        'preferred_updates', v_preferred_updates,
        'next_start_rank', v_next_start_rank,
        'next_after_score', v_last_score,
        'next_after_id', v_last_id,
        'total_scored', v_total_scored,
        'done', v_next_start_rank > v_total_scored
    );
END;
$$;

GRANT EXECUTE ON FUNCTION recalculate_auction_rankings_step(INTEGER, INTEGER, DECIMAL, UUID) TO service_role;
GRANT EXECUTE ON FUNCTION recalculate_auction_rankings_step(INTEGER, INTEGER, DECIMAL, UUID) TO authenticated;

COMMENT ON FUNCTION recalculate_auction_rankings_step IS
'Updates one ordered slice of auction rankings and preferred flags per call, returning a cursor for the next step.';
