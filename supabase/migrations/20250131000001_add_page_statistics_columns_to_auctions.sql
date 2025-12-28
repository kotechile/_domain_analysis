-- Add extracted columns from page_statistics JSONB to auctions table
-- This improves query performance and enables sorting/filtering on these fields

-- Add columns for page statistics data
ALTER TABLE auctions 
ADD COLUMN IF NOT EXISTS backlinks INTEGER,
ADD COLUMN IF NOT EXISTS referring_domains INTEGER,
ADD COLUMN IF NOT EXISTS backlinks_spam_score DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS first_seen TIMESTAMP WITH TIME ZONE;

-- Create indexes for performance on new columns
CREATE INDEX IF NOT EXISTS idx_auctions_backlinks 
ON auctions(backlinks) 
WHERE backlinks IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_auctions_referring_domains 
ON auctions(referring_domains) 
WHERE referring_domains IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_auctions_backlinks_spam_score 
ON auctions(backlinks_spam_score) 
WHERE backlinks_spam_score IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_auctions_first_seen 
ON auctions(first_seen) 
WHERE first_seen IS NOT NULL;

-- Add comments
COMMENT ON COLUMN auctions.backlinks IS 'Number of backlinks from DataForSEO page_statistics';
COMMENT ON COLUMN auctions.referring_domains IS 'Number of referring domains from DataForSEO page_statistics';
COMMENT ON COLUMN auctions.backlinks_spam_score IS 'Backlinks spam score from DataForSEO page_statistics';
COMMENT ON COLUMN auctions.first_seen IS 'First seen date from DataForSEO page_statistics or Wayback Machine';





