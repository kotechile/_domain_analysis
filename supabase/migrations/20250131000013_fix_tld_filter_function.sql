-- Fix TLD filter function to handle missing columns gracefully
-- This migration ensures the function works even if some columns don't exist yet

-- First, ensure all required columns exist (in case migrations weren't applied in order)
-- These columns are referenced by the TLD filter function

-- Ensure page_statistics column exists (from migration 20250130000000)
ALTER TABLE auctions
ADD COLUMN IF NOT EXISTS page_statistics JSONB;

-- Ensure extracted page_statistics columns exist (from migration 20250131000001)
ALTER TABLE auctions
ADD COLUMN IF NOT EXISTS backlinks INTEGER,
ADD COLUMN IF NOT EXISTS referring_domains INTEGER,
ADD COLUMN IF NOT EXISTS backlinks_spam_score DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS first_seen TIMESTAMP WITH TIME ZONE;

-- Ensure offer_type column exists (from migration 20250131000011)
ALTER TABLE auctions
ADD COLUMN IF NOT EXISTS offer_type VARCHAR(50);

-- Ensure current_bid column exists (from migration 20251211000001)
ALTER TABLE auctions
ADD COLUMN IF NOT EXISTS current_bid DECIMAL(10,2);

-- Ensure ranking column exists (from migration 20250125000002 - should already exist, but ensure it's there)
ALTER TABLE auctions
ADD COLUMN IF NOT EXISTS ranking INTEGER;

-- Ensure score column exists (from migration 20250125000002 - should already exist, but ensure it's there)
ALTER TABLE auctions
ADD COLUMN IF NOT EXISTS score DECIMAL(10,2);

-- Drop and recreate the function with proper error handling
-- First, try to drop with all possible signatures to ensure it's removed
DO $$ 
BEGIN
    -- Drop all possible variations of the function
    DROP FUNCTION IF EXISTS filter_auctions_by_tlds(TEXT[], BOOLEAN, VARCHAR(50), VARCHAR(50), BOOLEAN, BOOLEAN, INTEGER, INTEGER, DECIMAL(5,2), DECIMAL(5,2), DATE, DATE, VARCHAR(50), VARCHAR(10), INTEGER, INTEGER) CASCADE;
    DROP FUNCTION IF EXISTS count_auctions_by_tlds(TEXT[], BOOLEAN, VARCHAR(50), VARCHAR(50), BOOLEAN, BOOLEAN, INTEGER, INTEGER, DECIMAL(5,2), DECIMAL(5,2), DATE, DATE) CASCADE;
EXCEPTION WHEN OTHERS THEN
    -- If drop fails, continue - function might not exist
    RAISE NOTICE 'Function drop failed (this is OK if function does not exist): %', SQLERRM;
END $$;

-- Recreate filter_auctions_by_tlds function
CREATE OR REPLACE FUNCTION filter_auctions_by_tlds(
    p_tlds TEXT[],
    p_preferred BOOLEAN DEFAULT NULL,
    p_auction_site VARCHAR(50) DEFAULT NULL,
    p_offering_type VARCHAR(50) DEFAULT NULL,
    p_has_statistics BOOLEAN DEFAULT NULL,
    p_scored BOOLEAN DEFAULT NULL,
    p_min_rank INTEGER DEFAULT NULL,
    p_max_rank INTEGER DEFAULT NULL,
    p_min_score DECIMAL(5,2) DEFAULT NULL,
    p_max_score DECIMAL(5,2) DEFAULT NULL,
    p_expiration_from_date DATE DEFAULT NULL,
    p_expiration_to_date DATE DEFAULT NULL,
    p_sort_by VARCHAR(50) DEFAULT 'expiration_date',
    p_sort_order VARCHAR(10) DEFAULT 'asc',
    p_limit INTEGER DEFAULT 100,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    domain VARCHAR(255),
    start_date TIMESTAMP WITH TIME ZONE,
    expiration_date TIMESTAMP WITH TIME ZONE,
    auction_site VARCHAR(100),
    ranking INTEGER,
    score DECIMAL(10,2),
    preferred BOOLEAN,
    has_statistics BOOLEAN,
    backlinks INTEGER,
    referring_domains INTEGER,
    backlinks_spam_score DECIMAL(5,2),
    first_seen TIMESTAMP WITH TIME ZONE,
    current_bid DECIMAL(10,2),
    offer_type TEXT,  -- Use TEXT to match actual column type
    page_statistics JSONB,
    source_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.id,
        a.domain,
        a.start_date,
        a.expiration_date,
        a.auction_site,
        a.ranking,
        a.score,
        a.preferred,
        a.has_statistics,
        a.backlinks,
        a.referring_domains,
        a.backlinks_spam_score,
        a.first_seen,
        a.current_bid,
        a.offer_type,  -- TEXT type matches actual column
        a.page_statistics,
        a.source_data,
        a.created_at,
        a.updated_at
    FROM auctions a
    WHERE 
        -- Always filter to show only future expiration dates (expiration_date >= NOW())
        -- EXCEPT for buy_now records which might have NULL or far-future expiration dates
        (p_offering_type = 'buy_now' OR a.expiration_date >= NOW())
        -- TLD filtering: extract TLD from domain and check if it matches any in the array
        AND
        (p_tlds IS NULL OR array_length(p_tlds, 1) IS NULL OR 
         '.' || LOWER(SPLIT_PART(a.domain, '.', -1)) = ANY(
             SELECT UNNEST(ARRAY(
                 SELECT CASE 
                     WHEN tld LIKE '.%' THEN LOWER(tld)
                     ELSE LOWER('.' || tld)
                 END
                 FROM UNNEST(p_tlds) AS tld
             ))
         ))
        -- Other filters
        AND (p_preferred IS NULL OR a.preferred = p_preferred)
        AND (p_auction_site IS NULL OR a.auction_site = p_auction_site)
        AND (p_offering_type IS NULL OR LOWER(a.offer_type) = LOWER(p_offering_type))
        AND (p_has_statistics IS NULL OR a.has_statistics = p_has_statistics)
        AND (p_scored IS NULL OR (p_scored = TRUE AND a.score IS NOT NULL AND a.score > 0) OR (p_scored = FALSE AND (a.score IS NULL OR a.score <= 0)))
        AND (p_min_rank IS NULL OR a.ranking >= p_min_rank)
        AND (p_max_rank IS NULL OR a.ranking <= p_max_rank)
        AND (p_min_score IS NULL OR a.score >= p_min_score)
        AND (p_max_score IS NULL OR a.score <= p_max_score)
        AND (p_expiration_from_date IS NULL OR a.expiration_date >= p_expiration_from_date)
        AND (p_expiration_to_date IS NULL OR a.expiration_date <= p_expiration_to_date)
    ORDER BY
        CASE 
            WHEN p_sort_by = 'expiration_date' AND p_sort_order = 'asc' THEN a.expiration_date
        END ASC,
        CASE 
            WHEN p_sort_by = 'expiration_date' AND p_sort_order = 'desc' THEN a.expiration_date
        END DESC,
        CASE 
            WHEN p_sort_by = 'score' AND p_sort_order = 'asc' THEN a.score
        END ASC NULLS LAST,
        CASE 
            WHEN p_sort_by = 'score' AND p_sort_order = 'desc' THEN a.score
        END DESC NULLS LAST,
        CASE 
            WHEN p_sort_by = 'backlinks' AND p_sort_order = 'asc' THEN a.backlinks
        END ASC NULLS LAST,
        CASE 
            WHEN p_sort_by = 'backlinks' AND p_sort_order = 'desc' THEN a.backlinks
        END DESC NULLS LAST,
        CASE 
            WHEN p_sort_by = 'referring_domains' AND p_sort_order = 'asc' THEN a.referring_domains
        END ASC NULLS LAST,
        CASE 
            WHEN p_sort_by = 'referring_domains' AND p_sort_order = 'desc' THEN a.referring_domains
        END DESC NULLS LAST,
        CASE 
            WHEN p_sort_by = 'first_seen' AND p_sort_order = 'asc' THEN a.first_seen
        END ASC NULLS LAST,
        CASE 
            WHEN p_sort_by = 'first_seen' AND p_sort_order = 'desc' THEN a.first_seen
        END DESC NULLS LAST,
        CASE 
            WHEN p_sort_by = 'auction_site' AND p_sort_order = 'asc' THEN a.auction_site
        END ASC,
        CASE 
            WHEN p_sort_by = 'auction_site' AND p_sort_order = 'desc' THEN a.auction_site
        END DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$;

-- Recreate count_auctions_by_tlds function
CREATE OR REPLACE FUNCTION count_auctions_by_tlds(
    p_tlds TEXT[],
    p_preferred BOOLEAN DEFAULT NULL,
    p_auction_site VARCHAR(50) DEFAULT NULL,
    p_offering_type VARCHAR(50) DEFAULT NULL,
    p_has_statistics BOOLEAN DEFAULT NULL,
    p_scored BOOLEAN DEFAULT NULL,
    p_min_rank INTEGER DEFAULT NULL,
    p_max_rank INTEGER DEFAULT NULL,
    p_min_score DECIMAL(5,2) DEFAULT NULL,
    p_max_score DECIMAL(5,2) DEFAULT NULL,
    p_expiration_from_date DATE DEFAULT NULL,
    p_expiration_to_date DATE DEFAULT NULL
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COUNT(*)::INTEGER INTO v_count
    FROM auctions a
    WHERE 
        -- Always filter to show only future expiration dates (expiration_date >= NOW())
        -- EXCEPT for buy_now records which might have NULL or far-future expiration dates
        (p_offering_type = 'buy_now' OR a.expiration_date >= NOW())
        -- TLD filtering
        AND
        (p_tlds IS NULL OR array_length(p_tlds, 1) IS NULL OR 
         '.' || LOWER(SPLIT_PART(a.domain, '.', -1)) = ANY(
             SELECT UNNEST(ARRAY(
                 SELECT CASE 
                     WHEN tld LIKE '.%' THEN LOWER(tld)
                     ELSE LOWER('.' || tld)
                 END
                 FROM UNNEST(p_tlds) AS tld
             ))
         ))
        -- Other filters
        AND (p_preferred IS NULL OR a.preferred = p_preferred)
        AND (p_auction_site IS NULL OR a.auction_site = p_auction_site)
        AND (p_offering_type IS NULL OR LOWER(a.offer_type) = LOWER(p_offering_type))
        AND (p_has_statistics IS NULL OR a.has_statistics = p_has_statistics)
        AND (p_scored IS NULL OR (p_scored = TRUE AND a.score IS NOT NULL AND a.score > 0) OR (p_scored = FALSE AND (a.score IS NULL OR a.score <= 0)))
        AND (p_min_rank IS NULL OR a.ranking >= p_min_rank)
        AND (p_max_rank IS NULL OR a.ranking <= p_max_rank)
        AND (p_min_score IS NULL OR a.score >= p_min_score)
        AND (p_max_score IS NULL OR a.score <= p_max_score)
        AND (p_expiration_from_date IS NULL OR a.expiration_date >= p_expiration_from_date)
        AND (p_expiration_to_date IS NULL OR a.expiration_date <= p_expiration_to_date);
    
    RETURN COALESCE(v_count, 0);
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION filter_auctions_by_tlds TO service_role;
GRANT EXECUTE ON FUNCTION filter_auctions_by_tlds TO authenticated;
GRANT EXECUTE ON FUNCTION count_auctions_by_tlds TO service_role;
GRANT EXECUTE ON FUNCTION count_auctions_by_tlds TO authenticated;

