-- Full Domain Analysis Schema Initialization
-- This script safely inspects and creates/updates all necessary tables.
-- Run this in the Supabase SQL Editor.

-- 1. REPORTS TABLE (Main analysis reports)
CREATE TABLE IF NOT EXISTS reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_name VARCHAR(255) NOT NULL UNIQUE,
    analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    data_for_seo_metrics JSONB,
    wayback_machine_summary JSONB,
    llm_analysis JSONB,
    raw_data_links JSONB,
    processing_time_seconds FLOAT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ensure new columns exist (idempotent)
ALTER TABLE reports ADD COLUMN IF NOT EXISTS historical_data JSONB;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS detailed_data_available JSONB DEFAULT '{}';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS analysis_phase VARCHAR(50) DEFAULT 'essential';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS analysis_mode VARCHAR(20) DEFAULT 'legacy';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS progress_data JSONB;

-- 2. RAW DATA CACHE (API response caching)
CREATE TABLE IF NOT EXISTS raw_data_cache (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_name VARCHAR(255) NOT NULL,
    api_source VARCHAR(50) NOT NULL,
    json_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(domain_name, api_source)
);

-- 3. DETAILED ANALYSIS DATA (Backlinks, Keywords, etc.)
CREATE TABLE IF NOT EXISTS detailed_analysis_data (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_name VARCHAR(255) NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    json_data JSONB NOT NULL,
    task_id VARCHAR(255),
    data_source VARCHAR(50) DEFAULT 'dataforseo',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(domain_name, data_type)
);

-- 4. ASYNC TASKS (Background job tracking)
CREATE TABLE IF NOT EXISTS async_tasks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_name VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL UNIQUE,
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

-- 5. ANALYSIS MODE CONFIG (User preferences)
CREATE TABLE IF NOT EXISTS analysis_mode_config (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_name VARCHAR(255),
    mode_preference VARCHAR(20) DEFAULT 'dual',
    async_enabled BOOLEAN DEFAULT true,
    cache_ttl_hours INTEGER DEFAULT 24,
    manual_refresh_enabled BOOLEAN DEFAULT true,
    progress_indicators_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_analysis_mode_config_domain ON analysis_mode_config(domain_name);
-- Supabase specialized index for NULL values requires simpler handling or just rely on UUID if needed, but uniqueness on domain_name is key.
-- Note: unique index on NULL is allowed in Postgres (it treats NULL != NULL usually, but we can verify constraint logic).
-- For now, generic unique index on domain_name should suffice if we want per-domain config.

-- 6. BULK DOMAIN ANALYSIS (Bulk processing results)
CREATE TABLE IF NOT EXISTS bulk_domain_analysis (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_name VARCHAR(255) NOT NULL UNIQUE,
    provider VARCHAR(50),
    backlinks_bulk_page_summary JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. NAMECHEAP DOMAINS (Marketplace data)
CREATE TABLE IF NOT EXISTS namecheap_domains (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    url TEXT,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    price FLOAT,
    start_price FLOAT,
    renew_price FLOAT,
    bid_count INTEGER,
    ahrefs_domain_rating FLOAT,
    umbrella_ranking INTEGER,
    cloudflare_ranking INTEGER,
    estibot_value FLOAT,
    extensions_taken INTEGER,
    keyword_search_count INTEGER,
    registered_date TIMESTAMP WITH TIME ZONE,
    last_sold_price FLOAT,
    last_sold_year INTEGER,
    is_partner_sale BOOLEAN,
    semrush_a_score INTEGER,
    majestic_citation INTEGER,
    ahrefs_backlinks INTEGER,
    semrush_backlinks INTEGER,
    majestic_backlinks INTEGER,
    majestic_trust_flow FLOAT,
    go_value FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 8. INDEXES (Performance)
CREATE INDEX IF NOT EXISTS idx_reports_domain_name ON reports(domain_name);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_detailed_data_domain_type ON detailed_analysis_data(domain_name, data_type);
CREATE INDEX IF NOT EXISTS idx_async_tasks_status ON async_tasks(status);
CREATE INDEX IF NOT EXISTS idx_namecheap_domains_price ON namecheap_domains(price);
CREATE INDEX IF NOT EXISTS idx_namecheap_domains_dr ON namecheap_domains(ahrefs_domain_rating);

-- 9. ROW LEVEL SECURITY (Enable RLS for security)
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_data_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE detailed_analysis_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE async_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_mode_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE bulk_domain_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE namecheap_domains ENABLE ROW LEVEL SECURITY;

-- Create default policies (SERVICE ROLE access)
-- Update existing policies by dropping them first
DROP POLICY IF EXISTS "Service Role Full Access On Reports" ON reports;
CREATE POLICY "Service Role Full Access On Reports" ON reports FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service Role Full Access On Cache" ON raw_data_cache;
CREATE POLICY "Service Role Full Access On Cache" ON raw_data_cache FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service Role Full Access On Detailed Data" ON detailed_analysis_data;
CREATE POLICY "Service Role Full Access On Detailed Data" ON detailed_analysis_data FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service Role Full Access On Tasks" ON async_tasks;
CREATE POLICY "Service Role Full Access On Tasks" ON async_tasks FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service Role Full Access On Config" ON analysis_mode_config;
CREATE POLICY "Service Role Full Access On Config" ON analysis_mode_config FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service Role Full Access On Bulk" ON bulk_domain_analysis;
CREATE POLICY "Service Role Full Access On Bulk" ON bulk_domain_analysis FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service Role Full Access On Namecheap" ON namecheap_domains;
CREATE POLICY "Service Role Full Access On Namecheap" ON namecheap_domains FOR ALL USING (auth.role() = 'service_role');

-- Public Read Policies (Optional - Enable if frontend reads directly via Supabase client)
-- CREATE POLICY "Public Read Reports" ON reports FOR SELECT USING (true);
