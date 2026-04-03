-- Migration: Add to_delete column to auctions_staging table
-- This column is needed for the sync mechanism to work properly

-- Add to_delete column to auctions_staging table
ALTER TABLE auctions_staging
ADD COLUMN IF NOT EXISTS to_delete BOOLEAN DEFAULT FALSE;

-- Notify PostgREST to reload schema cache
NOTIFY pgrst, 'reload schema';

-- Create index for efficient queries on to_delete
CREATE INDEX IF NOT EXISTS idx_auctions_staging_to_delete
ON auctions_staging(to_delete)
WHERE to_delete = TRUE;

COMMENT ON COLUMN auctions_staging.to_delete IS 'Flag for sync mechanism: marked TRUE at start of import, set FALSE when record is updated, deleted at end if still TRUE';
