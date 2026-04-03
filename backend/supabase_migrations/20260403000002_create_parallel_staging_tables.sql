-- Migration: Create 5 parallel staging tables for concurrent upload processing
-- Tables: auctions_staging_0 through auctions_staging_4

-- Create 5 staging tables (LIKE copies structure including indexes, constraints, etc.)
DO $$
BEGIN
    FOR i IN 0..4 LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS auctions_staging_%s (LIKE auctions_staging INCLUDING ALL)',
            i
        );

        -- Add unique index for job_id isolation
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_auctions_staging_%s_job_id ON auctions_staging_%s(job_id)',
            i, i
        );

        -- Add index for domain lookups during merge
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_auctions_staging_%s_domain ON auctions_staging_%s(domain)',
            i, i
        );

        -- Add composite index for merge operations (job_id + unique constraint columns)
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_auctions_staging_%s_merge ON auctions_staging_%s(job_id, domain, auction_site, expiration_date)',
            i, i
        );
    END LOOP;
END $$;

-- Grant permissions to service_role
GRANT USAGE ON SCHEMA public TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO service_role;

-- Notify PostgREST to reload schema cache
NOTIFY pgrst, 'reload schema';
