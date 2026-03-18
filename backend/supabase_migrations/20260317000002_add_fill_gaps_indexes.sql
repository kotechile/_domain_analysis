-- Migration: Add index for Fill Gaps / Bulk Refresh query performance
-- This optimizes the query that checks for domains missing metrics

-- Index for the staleness check (updated_at > 7 days ago)
CREATE INDEX IF NOT EXISTS idx_auctions_updated_at
ON auctions(updated_at)
WHERE updated_at IS NOT NULL;

-- Composite index for the Fill Gaps query pattern:
-- score > 0 AND (expiration_date check) AND NOT recently updated
CREATE INDEX IF NOT EXISTS idx_auctions_fill_gaps
ON auctions(score, expiration_date, updated_at)
WHERE score > 0 AND to_delete = FALSE;

-- Partial index for domains with page_statistics (has metrics)
CREATE INDEX IF NOT EXISTS idx_auctions_has_page_stats
ON auctions(domain)
WHERE page_statistics IS NOT NULL;

-- Partial index for domains without page_statistics (missing metrics)
CREATE INDEX IF NOT EXISTS idx_auctions_no_page_stats
ON auctions(domain, score, expiration_date)
WHERE page_statistics IS NULL AND score > 0 AND to_delete = FALSE;

COMMENT ON INDEX idx_auctions_updated_at IS 'Optimizes staleness check for bulk refresh';
COMMENT ON INDEX idx_auctions_fill_gaps IS 'Optimizes Fill Gaps query with score, expiration, and staleness checks';
