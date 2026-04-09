-- Separate intrinsic domain quality ranking from external opportunity metrics.
-- This prevents DataForSEO rank data from colliding with the auction name-quality rank.

ALTER TABLE auctions
ADD COLUMN IF NOT EXISTS name_rank INTEGER,
ADD COLUMN IF NOT EXISTS name_preferred BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS opportunity_rank INTEGER,
ADD COLUMN IF NOT EXISTS opportunity_score DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS organic_search_rank INTEGER,
ADD COLUMN IF NOT EXISTS opportunity_score_updated_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX IF NOT EXISTS idx_auctions_name_rank ON auctions(name_rank);
CREATE INDEX IF NOT EXISTS idx_auctions_opportunity_rank ON auctions(opportunity_rank);
CREATE INDEX IF NOT EXISTS idx_auctions_opportunity_score ON auctions(opportunity_score);
CREATE INDEX IF NOT EXISTS idx_auctions_organic_search_rank ON auctions(organic_search_rank);

UPDATE auctions
SET
    name_rank = COALESCE(name_rank, ranking),
    name_preferred = COALESCE(name_preferred, preferred)
WHERE ranking IS NOT NULL
   OR preferred IS NOT NULL;
