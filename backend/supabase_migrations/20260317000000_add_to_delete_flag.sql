-- Migration: Add to_delete flag for auction sync mechanism
-- This allows marking auctions for deletion during file processing

-- Add to_delete column to auctions table
ALTER TABLE auctions
ADD COLUMN IF NOT EXISTS to_delete BOOLEAN DEFAULT FALSE;

-- Create index for efficient queries
CREATE INDEX IF NOT EXISTS idx_auctions_to_delete
ON auctions(to_delete)
WHERE to_delete = TRUE;

-- Create index for auction_site + to_delete combination
CREATE INDEX IF NOT EXISTS idx_auctions_site_to_delete
ON auctions(auction_site, to_delete);

-- Add comment explaining the column
COMMENT ON COLUMN auctions.to_delete IS 'Flag for sync mechanism: marked TRUE at start of import, set FALSE when record is updated, deleted at end if still TRUE';
