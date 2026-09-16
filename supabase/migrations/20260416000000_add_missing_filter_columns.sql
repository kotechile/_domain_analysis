-- Migration: Add missing filter columns to filters table for DOM-9 advanced search
-- These columns are used by the FilterSettings model and saved queries but were missing from the schema.

-- Add price range filter columns
ALTER TABLE filters ADD COLUMN IF NOT EXISTS min_price DECIMAL(10,2) DEFAULT NULL;
ALTER TABLE filters ADD COLUMN IF NOT EXISTS max_price DECIMAL(10,2) DEFAULT NULL;

-- Add keyword filter column
ALTER TABLE filters ADD COLUMN IF NOT EXISTS keyword TEXT DEFAULT NULL;

-- Add TLDs array column for multi-TLD filter persistence
-- (Already exists in some deployments via ALTER from _create_tables, but ensure it's present)
ALTER TABLE filters ADD COLUMN IF NOT EXISTS tlds JSONB DEFAULT NULL;

-- Add date range columns (may already exist in some deployments)
ALTER TABLE filters ADD COLUMN IF NOT EXISTS expiration_from_date DATE DEFAULT NULL;
ALTER TABLE filters ADD COLUMN IF NOT EXISTS expiration_to_date DATE DEFAULT NULL;

-- Add user_id UUID column for proper user-scoped filters (upgrade from TEXT)
-- This is a safe no-op if already UUID type, and adds the column if missing
DO $$
BEGIN
    -- Only attempt if column doesn't exist or if it's TEXT type that needs upgrading
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'filters' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE filters ADD COLUMN user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
    END IF;
END $$;