-- Add link column to auctions table for storing auction URLs (e.g., GoDaddy auction links)
ALTER TABLE auctions 
ADD COLUMN IF NOT EXISTS link TEXT;

-- Add link column to auctions_staging table
ALTER TABLE auctions_staging 
ADD COLUMN IF NOT EXISTS link TEXT;

-- Create index for link queries
CREATE INDEX IF NOT EXISTS idx_auctions_link ON auctions(link) WHERE link IS NOT NULL;

-- Add comment
COMMENT ON COLUMN auctions.link IS 'Direct link to the auction listing page (e.g., GoDaddy auction URL)';





