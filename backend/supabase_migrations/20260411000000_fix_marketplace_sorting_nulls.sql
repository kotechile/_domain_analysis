-- Create a function to fetch auctions with flexible sorting and NULLS LAST for numeric metrics.
-- This solves the issue where NULL values appear at the top during DESC sorts in the marketplace.

CREATE OR REPLACE FUNCTION public.get_auctions_with_stats_sorted(
    p_filters JSONB DEFAULT '{}',
    p_sort_by TEXT DEFAULT 'expiration_date',
    p_order TEXT DEFAULT 'asc',
    p_limit INTEGER DEFAULT 100,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    domain TEXT,
    auction_site TEXT,
    expiration_date TIMESTAMP WITH TIME ZONE,
    current_bid NUMERIC,
    offer_type TEXT,
    score NUMERIC,
    domain_rating INTEGER,
    organic_traffic INTEGER,
    keywords_count INTEGER,
    backlinks INTEGER,
    backlinks_spam_score INTEGER,
    preferred BOOLEAN,
    has_statistics BOOLEAN,
    to_delete BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    page_statistics JSONB
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_query TEXT;
BEGIN
    -- Start building the base query
    v_query := 'SELECT
        id, domain, auction_site, expiration_date, current_bid, offer_type,
        score, domain_rating, organic_traffic, keywords_count, backlinks,
        backlinks_spam_score, preferred, has_statistics, to_delete,
        created_at, updated_at, page_statistics
        FROM auctions
        WHERE to_delete = false';

    -- Apply Dynamic Filters from JSONB
    IF p_filters ->> 'search' IS NOT NULL THEN
        v_query := v_query || ' AND domain ILIKE ' || quote_literal('%' || (p_filters ->> 'search') || '%');
    END IF;

    IF (p_filters ->> 'preferred') IS NOT NULL THEN
        v_query := v_query || ' AND preferred = ' || (p_filters ->> 'preferred')::BOOLEAN;
    END IF;

    IF (p_filters ->> 'scored') IS NOT NULL THEN
        IF (p_filters ->> 'scored')::BOOLEAN THEN
            v_query := v_query || ' AND score > 0';
        ELSE
            v_query := v_query || ' AND (score = 0 OR score IS NULL)';
        END IF;
    END IF;

    IF (p_filters ->> 'has_statistics') IS NOT NULL THEN
        v_query := v_query || ' AND has_statistics = ' || (p_filters ->> 'has_statistics')::BOOLEAN;
    END IF;

    IF (p_filters ->> 'expiration_from_date') IS NOT NULL THEN
        v_query := v_query || ' AND expiration_date >= ' || quote_literal(p_filters ->> 'expiration_from_date');
    END IF;

    IF (p_filters ->> 'expiration_to_date') IS NOT NULL THEN
        v_query := v_query || ' AND expiration_date <= ' || quote_literal(p_filters ->> 'expiration_to_date');
    END IF;

    IF p_filters ? 'auction_sites' THEN
        v_query := v_query || ' AND auction_site = ANY(ARRAY' ||
                   (SELECT string_agg('''' || val || '''', ',') FROM jsonb_array_elements_text(p_filters->'auction_sites') AS val) || ')';
    END IF;

    IF p_filters ? 'tlds' THEN
        -- Simple implementation for TLDs: domain ends with any of the provided TLDs
        v_query := v_query || ' AND (';
        SELECT v_query || string_agg('domain ILIKE ' || quote_literal('%' || val || ''), ' OR ')
        INTO v_query
        FROM jsonb_array_elements_text(p_filters->'tlds') AS val;
        v_query := v_query || ')';
    END IF;

    IF p_filters ->> 'offering_type' IS NOT NULL THEN
        v_query := v_query || ' AND offer_type = ' || quote_literal(p_filters ->> 'offering_type');
    END IF;

    IF (p_filters ->> 'min_score') IS NOT NULL THEN
        v_query := v_query || ' AND score >= ' || (p_filters ->> 'min_score')::NUMERIC;
    END IF;

    IF (p_filters ->> 'max_score') IS NOT NULL THEN
        v_query := v_query || ' AND score <= ' || (p_filters ->> 'max_score')::NUMERIC;
    END IF;

    -- Default: Only show not expired
    IF (p_filters ->> 'expiration_from_date') IS NULL AND (p_filters ->> 'search') IS NULL THEN
        v_query := v_query || ' AND expiration_date >= NOW()';
    END IF;

    -- Apply Sorting with NULLS LAST
    v_query := v_query || ' ORDER BY ';

    IF p_order = 'desc' THEN
        -- Numeric metrics that need NULLS LAST
        IF p_sort_by IN ('domain_rating', 'organic_traffic', 'keywords_count', 'backlinks', 'score') THEN
            v_query := v_query || quote_ident(p_sort_by) || ' DESC NULLS LAST';
        ELSE
            v_query := v_query || quote_ident(p_sort_by) || ' DESC';
        END IF;
        v_query := v_query || ', domain DESC';
    ELSE
        v_query := v_query || quote_ident(p_sort_by) || ' ASC';
        v_query := v_query || ', domain ASC';
    END IF;

    -- Pagination
    v_query := v_query || ' LIMIT ' || p_limit || ' OFFSET ' || p_offset;

    RETURN QUERY EXECUTE v_query;
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_auctions_with_stats_sorted TO service_role;
GRANT EXECUTE ON FUNCTION public.get_auctions_with_stats_sorted TO authenticated;
