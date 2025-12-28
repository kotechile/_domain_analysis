-- Add page_statistics JSONB field to auctions table
-- This field will store DataForSEO page summary statistics

ALTER TABLE auctions 
ADD COLUMN IF NOT EXISTS page_statistics JSONB;

-- Create index for efficient queries on page_statistics
CREATE INDEX IF NOT EXISTS idx_auctions_page_statistics 
ON auctions USING GIN (page_statistics) 
WHERE page_statistics IS NOT NULL;

-- Create index for finding domains without page_statistics
CREATE INDEX IF NOT EXISTS idx_auctions_no_page_stats 
ON auctions(created_at DESC, score DESC) 
WHERE page_statistics IS NULL AND score IS NOT NULL;

-- Add comment
COMMENT ON COLUMN auctions.page_statistics IS 'DataForSEO page summary statistics stored as JSONB';



