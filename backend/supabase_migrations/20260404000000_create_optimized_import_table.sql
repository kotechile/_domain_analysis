-- Performance-Optimized Auction Import System
-- Replaces the 5-table parallel approach with a single, efficient staging table
-- Uses PostgreSQL COPY protocol for maximum insert performance

-- Drop old parallel staging tables if they exist
DROP TABLE IF EXISTS auctions_staging_0 CASCADE;
DROP TABLE IF EXISTS auctions_staging_1 CASCADE;
DROP TABLE IF EXISTS auctions_staging_2 CASCADE;
DROP TABLE IF EXISTS auctions_staging_3 CASCADE;
DROP TABLE IF EXISTS auctions_staging_4 CASCADE;

-- Drop old single staging table
DROP TABLE IF EXISTS auctions_staging CASCADE;

-- Create optimized single staging table
CREATE TABLE IF NOT EXISTS auctions_import (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    auction_site VARCHAR(100) NOT NULL,
    expiration_date TIMESTAMPTZ NOT NULL,
    start_date TIMESTAMPTZ,
    current_bid DOUBLE PRECISION,
    link TEXT,
    offer_type VARCHAR(50),
    source_data JSONB,
    first_seen TEXT,
    import_batch_id UUID NOT NULL,  -- Groups records from same upload
    import_timestamp TIMESTAMPTZ DEFAULT NOW(),

    -- Index for fast cleanup
    CONSTRAINT idx_auctions_import_batch UNIQUE (import_batch_id, domain, auction_site)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_auctions_import_batch_lookup
ON auctions_import(import_batch_id);

CREATE INDEX IF NOT EXISTS idx_auctions_import_domain
ON auctions_import(domain);

CREATE INDEX IF NOT EXISTS idx_auctions_import_site
ON auctions_import(auction_site);

-- Add last_import_batch_id to auctions table for tracking
ALTER TABLE auctions
ADD COLUMN IF NOT EXISTS last_import_batch_id UUID,
ADD COLUMN IF NOT EXISTS last_import_timestamp TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_auctions_last_import
ON auctions(last_import_batch_id)
WHERE last_import_batch_id IS NOT NULL;

-- Notify PostgREST to reload schema
NOTIFY pgrst, 'reload schema';
