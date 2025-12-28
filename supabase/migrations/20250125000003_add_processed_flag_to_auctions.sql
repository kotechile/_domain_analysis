-- Add processed flag to auctions table to track which records have been scored
ALTER TABLE auctions ADD COLUMN IF NOT EXISTS processed BOOLEAN DEFAULT FALSE;

-- Create index for performance when querying unprocessed records
CREATE INDEX IF NOT EXISTS idx_auctions_processed ON auctions(processed, expiration_date) WHERE processed = FALSE;

-- Update existing records with scores to be marked as processed
UPDATE auctions SET processed = TRUE WHERE score IS NOT NULL;

