-- FIX AUCTIONS STAGING SCHEMA - Complete rebuild
-- This migration rebuilds the auctions_staging table with the correct columns

-- 1. Drop the old staging table (we'll lose staging data, but that's fine - it's just staging)
DROP TABLE IF EXISTS auctions_staging CASCADE;

-- 2. Create the staging table with the CORRECT schema matching what the code expects
CREATE TABLE auctions_staging (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain VARCHAR(255) NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE,
    expiration_date TIMESTAMP WITH TIME ZONE,
    auction_site VARCHAR(50),
    current_bid DECIMAL(12, 2),
    source_data JSONB,
    link TEXT,
    processed BOOLEAN DEFAULT FALSE,
    preferred BOOLEAN DEFAULT FALSE,
    has_statistics BOOLEAN DEFAULT FALSE,
    score DECIMAL(5, 2),
    ranking INTEGER,
    first_seen TIMESTAMP WITH TIME ZONE,
    deletion_flag BOOLEAN DEFAULT FALSE,
    offer_type VARCHAR(50) DEFAULT 'auction',
    job_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Create indexes for efficient queries
CREATE INDEX idx_auctions_staging_job_id ON auctions_staging(job_id);
CREATE INDEX idx_auctions_staging_domain ON auctions_staging(domain);
CREATE INDEX idx_auctions_staging_auction_site ON auctions_staging(auction_site);
CREATE INDEX idx_auctions_staging_offer_type ON auctions_staging(offer_type);

-- 4. Enable RLS
ALTER TABLE auctions_staging ENABLE ROW LEVEL SECURITY;

-- 5. Policy: Service role full access
CREATE POLICY "Service Role Full Access On Staging" ON auctions_staging
    FOR ALL USING (auth.role() = 'service_role');

-- 6. Ensure job_id exists in main auctions table too
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'auctions' AND column_name = 'job_id') THEN
        ALTER TABLE auctions ADD COLUMN job_id UUID;
        CREATE INDEX IF NOT EXISTS idx_auctions_job_id ON auctions(job_id);
    END IF;
END $$;

-- 7. Also ensure main auctions table has offer_type column
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'auctions' AND column_name = 'offer_type') THEN
        ALTER TABLE auctions ADD COLUMN offer_type VARCHAR(50) DEFAULT 'auction';
    END IF;
END $$;

-- 8. Verify the schema
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'auctions_staging'
ORDER BY ordinal_position;
