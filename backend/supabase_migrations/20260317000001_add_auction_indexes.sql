-- Migration: Add performance indexes for auctions marketplace queries
-- These indexes optimize the get_auctions_with_statistics query

-- Index for expiration_date (most common filter - default is gte now)
CREATE INDEX IF NOT EXISTS idx_auctions_expiration_date
ON auctions(expiration_date);

-- Composite index for common filter combination
CREATE INDEX IF NOT EXISTS idx_auctions_site_expiration
ON auctions(auction_site, expiration_date);

-- Index for score filtering (scored/unscored, min/max score)
CREATE INDEX IF NOT EXISTS idx_auctions_score
ON auctions(score)
WHERE score IS NOT NULL;

-- Index for has_statistics flag
CREATE INDEX IF NOT EXISTS idx_auctions_has_statistics
ON auctions(has_statistics)
WHERE has_statistics = true;

-- Index for preferred flag
CREATE INDEX IF NOT EXISTS idx_auctions_preferred
ON auctions(preferred)
WHERE preferred = true;

-- Index for offer_type filtering
CREATE INDEX IF NOT EXISTS idx_auctions_offer_type
ON auctions(offer_type);

-- Index for ranking sorting/filtering
CREATE INDEX IF NOT EXISTS idx_auctions_ranking
ON auctions(ranking)
WHERE ranking IS NOT NULL;

-- Partial index for active auctions (not expired) - most common query pattern
CREATE INDEX IF NOT EXISTS idx_auctions_active
ON auctions(expiration_date, auction_site, score)
WHERE expiration_date > NOW();

-- Index for domain TLD filtering (suffix matching won't use index efficiently,
-- but we can index the domain for exact lookups)
CREATE INDEX IF NOT EXISTS idx_auctions_domain
ON auctions(domain);

COMMENT ON INDEX idx_auctions_expiration_date IS 'Optimizes default expiration_date >= NOW() filter';
COMMENT ON INDEX idx_auctions_site_expiration IS 'Optimizes common auction_site + expiration_date queries';
COMMENT ON INDEX idx_auctions_score IS 'Optimizes scored/unscored and score range filters';
COMMENT ON INDEX idx_auctions_active IS 'Optimizes the most common query: active auctions by site with score';
