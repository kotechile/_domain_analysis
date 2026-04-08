-- Derive referring domains directly from domain_backlinks.
-- This replaces the need for a separate domain_referring_domains table.

CREATE INDEX IF NOT EXISTS idx_domain_backlinks_refdomains_lookup
ON domain_backlinks(domain_name, domain_name_source, dr DESC);

CREATE OR REPLACE FUNCTION public.get_referring_domains_from_backlinks(
    p_domain_name TEXT,
    p_limit INTEGER DEFAULT 100,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    referring_domain VARCHAR(255),
    backlinks_count BIGINT,
    dr INTEGER,
    anchor_text TEXT,
    first_seen TEXT,
    last_seen TEXT,
    total_count BIGINT
)
LANGUAGE sql
SECURITY DEFINER
AS $$
    WITH aggregated AS (
        SELECT
            domain_name_source::VARCHAR(255) AS referring_domain,
            COUNT(*)::BIGINT AS backlinks_count,
            MAX(COALESCE(dr, 0))::INTEGER AS dr
        FROM domain_backlinks
        WHERE domain_name = p_domain_name
          AND domain_name_source IS NOT NULL
          AND domain_name_source <> ''
        GROUP BY domain_name_source
    ),
    counted AS (
        SELECT
            referring_domain,
            backlinks_count,
            dr,
            COUNT(*) OVER () AS total_count
        FROM aggregated
    )
    SELECT
        referring_domain,
        backlinks_count,
        dr,
        ''::TEXT AS anchor_text,
        ''::TEXT AS first_seen,
        ''::TEXT AS last_seen,
        total_count
    FROM counted
    ORDER BY dr DESC NULLS LAST, backlinks_count DESC, referring_domain ASC
    LIMIT GREATEST(p_limit, 0)
    OFFSET GREATEST(p_offset, 0);
$$;

REVOKE ALL ON FUNCTION public.get_referring_domains_from_backlinks(TEXT, INTEGER, INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_referring_domains_from_backlinks(TEXT, INTEGER, INTEGER) TO service_role;
