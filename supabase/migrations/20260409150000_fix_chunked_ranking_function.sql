-- Safer chunked ranking recalculation for large datasets.
-- The original chunked function still ended with a full-table ranking update,
-- which defeats the purpose on multi-million-row datasets.

CREATE INDEX IF NOT EXISTS idx_auctions_score_desc_id
ON auctions (score DESC, id)
WHERE score IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_auctions_ranking_not_null
ON auctions (ranking)
WHERE ranking IS NOT NULL;

CREATE OR REPLACE FUNCTION recalculate_auction_rankings_chunked(
    p_batch_size INTEGER DEFAULT 25000
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_total_scored INTEGER := 0;
    v_total_ranked INTEGER := 0;
    v_total_preferred INTEGER := 0;
    v_batch_ranked INTEGER := 0;
    v_batch_preferred INTEGER := 0;
    v_batches_processed INTEGER := 0;
    v_preferred_batches_processed INTEGER := 0;
    v_offset INTEGER := 0;
    v_start_time TIMESTAMP;
    v_end_time TIMESTAMP;
    v_score_threshold DECIMAL(10,2);
    v_rank_threshold INTEGER;
    v_use_both_thresholds BOOLEAN;
BEGIN
    v_start_time := clock_timestamp();

    IF p_batch_size IS NULL OR p_batch_size <= 0 THEN
        p_batch_size := 25000;
    END IF;

    SELECT COUNT(*)
    INTO v_total_scored
    FROM auctions
    WHERE score IS NOT NULL;

    IF v_total_scored = 0 THEN
        RETURN jsonb_build_object(
            'success', TRUE,
            'ranked_count', 0,
            'preferred_count', 0,
            'batches_processed', 0,
            'message', 'No scored records found'
        );
    END IF;

    -- Recalculate rankings in deterministic chunks ordered by score and id.
    WHILE v_offset < v_total_scored LOOP
        WITH batch AS (
            SELECT id, score
            FROM auctions
            WHERE score IS NOT NULL
            ORDER BY score DESC, id ASC
            OFFSET v_offset
            LIMIT p_batch_size
        ),
        ranked_batch AS (
            SELECT
                id,
                ROW_NUMBER() OVER (ORDER BY score DESC, id ASC) + v_offset AS new_ranking
            FROM batch
        )
        UPDATE auctions a
        SET
            ranking = rb.new_ranking,
            updated_at = NOW()
        FROM ranked_batch rb
        WHERE a.id = rb.id
        AND (a.ranking IS NULL OR a.ranking IS DISTINCT FROM rb.new_ranking);

        GET DIAGNOSTICS v_batch_ranked = ROW_COUNT;
        v_total_ranked := v_total_ranked + v_batch_ranked;
        v_batches_processed := v_batches_processed + 1;
        v_offset := v_offset + p_batch_size;
    END LOOP;

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
        v_offset := 1;

        WHILE v_offset <= v_total_scored LOOP
            UPDATE auctions a
            SET
                preferred = CASE
                    WHEN v_score_threshold IS NULL AND v_rank_threshold IS NULL THEN TRUE
                    WHEN v_use_both_thresholds THEN
                        (v_score_threshold IS NULL OR a.score >= v_score_threshold) AND
                        (v_rank_threshold IS NULL OR a.ranking <= v_rank_threshold)
                    ELSE
                        (v_score_threshold IS NULL OR a.score >= v_score_threshold) OR
                        (v_rank_threshold IS NULL OR a.ranking <= v_rank_threshold)
                END,
                updated_at = NOW()
            WHERE a.score IS NOT NULL
            AND a.ranking BETWEEN v_offset AND (v_offset + p_batch_size - 1)
            AND (
                a.preferred IS NULL
                OR a.preferred IS DISTINCT FROM
                    CASE
                        WHEN v_score_threshold IS NULL AND v_rank_threshold IS NULL THEN TRUE
                        WHEN v_use_both_thresholds THEN
                            (v_score_threshold IS NULL OR a.score >= v_score_threshold) AND
                            (v_rank_threshold IS NULL OR a.ranking <= v_rank_threshold)
                        ELSE
                            (v_score_threshold IS NULL OR a.score >= v_score_threshold) OR
                            (v_rank_threshold IS NULL OR a.ranking <= v_rank_threshold)
                    END
            );

            GET DIAGNOSTICS v_batch_preferred = ROW_COUNT;
            v_total_preferred := v_total_preferred + v_batch_preferred;
            v_preferred_batches_processed := v_preferred_batches_processed + 1;
            v_offset := v_offset + p_batch_size;
        END LOOP;
    END IF;

    v_end_time := clock_timestamp();

    RETURN jsonb_build_object(
        'success', TRUE,
        'ranked_count', v_total_ranked,
        'preferred_count', v_total_preferred,
        'total_scored', v_total_scored,
        'batches_processed', v_batches_processed,
        'preferred_batches_processed', v_preferred_batches_processed,
        'batch_size', p_batch_size,
        'execution_time_seconds', EXTRACT(EPOCH FROM (v_end_time - v_start_time))
    );
END;
$$;

GRANT EXECUTE ON FUNCTION recalculate_auction_rankings_chunked(INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION recalculate_auction_rankings_chunked(INTEGER) TO authenticated;

COMMENT ON FUNCTION recalculate_auction_rankings_chunked IS
'Chunked ranking recalculation that updates rankings and preferred flags in batches to avoid statement timeouts on large datasets.';
