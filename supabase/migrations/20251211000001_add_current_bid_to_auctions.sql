-- Add current_bid column to auctions table
ALTER TABLE auctions 
ADD COLUMN IF NOT EXISTS current_bid DECIMAL(10,2);

-- Create index for current_bid queries
CREATE INDEX IF NOT EXISTS idx_auctions_current_bid ON auctions(current_bid) WHERE current_bid IS NOT NULL;

-- Add comment
COMMENT ON COLUMN auctions.current_bid IS 'Current bid amount for the domain auction';








