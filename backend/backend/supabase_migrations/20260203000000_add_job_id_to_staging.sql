-- Migration: Add job_id to auctions_staging for isolation
-- This allows multiple concurrent uploads to use the same staging table without interfering with each other.

-- 1. Add job_id column
ALTER TABLE auctions_staging ADD COLUMN IF NOT EXISTS job_id UUID;

-- 2. Create index for performance
CREATE INDEX IF NOT EXISTS idx_auctions_staging_job_id ON auctions_staging(job_id);

-- 3. Update existing indexes to include job_id if necessary, 
-- but for now a separate index is sufficient for the clear/merge filters.
