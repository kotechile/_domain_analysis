-- FIX AUCTIONS STAGING SCHEMA
-- This script ensures the `auctions_staging` table exists and has the required `job_id` column.

-- 1. Create table if it doesn't exist (basic schema, add columns as needed)
CREATE TABLE IF NOT EXISTS auctions_staging (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain VARCHAR(255),
    price DECIMAL(10, 2),
    bids INTEGER,
    end_date TIMESTAMP WITH TIME ZONE,
    auction_site VARCHAR(50),
    status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Add job_id column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'auctions_staging' AND column_name = 'job_id') THEN
        ALTER TABLE auctions_staging ADD COLUMN job_id UUID;
    END IF;
END $$;

-- 3. Create index for job_id
CREATE INDEX IF NOT EXISTS idx_auctions_staging_job_id ON auctions_staging(job_id);

-- 4. Enable RLS
ALTER TABLE auctions_staging ENABLE ROW LEVEL SECURITY;

-- 5. Policy: Service role full access
DROP POLICY IF EXISTS "Service Role Full Access On Staging" ON auctions_staging;
CREATE POLICY "Service Role Full Access On Staging" ON auctions_staging FOR ALL USING (auth.role() = 'service_role');


-- 6. CRITICAL: Add job_id to MAIN auctions table too
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'auctions' AND column_name = 'job_id') THEN
        ALTER TABLE auctions ADD COLUMN job_id UUID;
        
        -- Create index for faster lookups/deletions by job
        CREATE INDEX IF NOT EXISTS idx_auctions_job_id ON auctions(job_id);
    END IF;
END $$;
