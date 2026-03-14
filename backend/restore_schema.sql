-- RESTORE SCHEMA SCRIPT
-- This script restores the `user_resource_usage` table and ensures all standard tables exist.
-- Run this in the Supabase SQL Editor.

-- ==========================================
-- 1. Restore `user_resource_usage` Table
-- ==========================================

CREATE TABLE IF NOT EXISTS user_resource_usage (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    resource_type VARCHAR(50) NOT NULL, -- 'llm', 'dataforseo', etc.
    operation VARCHAR(100) NOT NULL, -- 'generate_analysis', 'domain_rank_overview', etc.
    provider VARCHAR(50), -- 'openai', 'gemini', 'dataforseo'
    model VARCHAR(100), -- 'gpt-4o', 'gemini-1.5-pro', or 'v3' for dataforseo
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost_estimated DECIMAL(10, 6) DEFAULT 0, -- Estimated cost in USD
    details JSONB DEFAULT '{}'::JSONB, -- Extra details like response time, usage breakdown
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster querying by user and date
CREATE INDEX IF NOT EXISTS idx_user_resource_usage_user_id ON user_resource_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_user_resource_usage_created_at ON user_resource_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_user_resource_usage_resource_type ON user_resource_usage(resource_type);

-- Enable RLS
ALTER TABLE user_resource_usage ENABLE ROW LEVEL SECURITY;

-- Policy: Users can see their own usage
DROP POLICY IF EXISTS "Users can view their own usage" ON user_resource_usage;
CREATE POLICY "Users can view their own usage" 
ON user_resource_usage FOR SELECT 
TO authenticated 
USING (auth.uid() = user_id);

-- Policy: Service role can do everything (insert, select, etc.)
DROP POLICY IF EXISTS "Service role full access" ON user_resource_usage;
CREATE POLICY "Service role full access" 
ON user_resource_usage FOR ALL 
TO service_role 
USING (true) 
WITH CHECK (true);


-- ==========================================
-- 2. Ensure Standard Tables Exist (Idempotent)
-- ==========================================

-- REPORTS TABLE
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

-- Ensure new columns exist for reports
ALTER TABLE reports ADD COLUMN IF NOT EXISTS historical_data JSONB;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS detailed_data_available JSONB DEFAULT '{}';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS analysis_phase VARCHAR(50) DEFAULT 'essential';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS analysis_mode VARCHAR(20) DEFAULT 'legacy';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS progress_data JSONB;

-- RAW DATA CACHE
CREATE TABLE IF NOT EXISTS raw_data_cache (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_name VARCHAR(255) NOT NULL,
    api_source VARCHAR(50) NOT NULL,
    json_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(domain_name, api_source)
);

-- DETAILED ANALYSIS DATA
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

-- ASYNC TASKS
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

-- ANALYSIS MODE CONFIG
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

-- BULK DOMAIN ANALYSIS
CREATE TABLE IF NOT EXISTS bulk_domain_analysis (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_name VARCHAR(255) NOT NULL UNIQUE,
    provider VARCHAR(50),
    backlinks_bulk_page_summary JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- NAMECHEAP DOMAINS
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

-- START: Add missing columns to namecheap_domains if they don't exist (based on recent migrations found in file list)
ALTER TABLE namecheap_domains ADD COLUMN IF NOT EXISTS scoring_stats JSONB;
-- END: Add missing columns

-- SECRETS TABLE
CREATE TABLE IF NOT EXISTS secrets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL UNIQUE,
    credentials JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id),
    updated_by UUID REFERENCES auth.users(id)
);


-- ==========================================
-- 3. Restore Indexes
-- ==========================================

CREATE INDEX IF NOT EXISTS idx_reports_domain_name ON reports(domain_name);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_detailed_data_domain_type ON detailed_analysis_data(domain_name, data_type);
CREATE INDEX IF NOT EXISTS idx_async_tasks_status ON async_tasks(status);
CREATE INDEX IF NOT EXISTS idx_namecheap_domains_price ON namecheap_domains(price);
CREATE INDEX IF NOT EXISTS idx_namecheap_domains_dr ON namecheap_domains(ahrefs_domain_rating);
CREATE INDEX IF NOT EXISTS idx_secrets_service_name ON secrets(service_name);


-- ==========================================
-- 4. Enable Row Level Security (RLS)
-- ==========================================

ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_data_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE detailed_analysis_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE async_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_mode_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE bulk_domain_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE namecheap_domains ENABLE ROW LEVEL SECURITY;
ALTER TABLE secrets ENABLE ROW LEVEL SECURITY;


-- ==========================================
-- 5. Restore RLS Policies (Service Role Access)
-- ==========================================

-- Reports
DROP POLICY IF EXISTS "Service Role Full Access On Reports" ON reports;
CREATE POLICY "Service Role Full Access On Reports" ON reports FOR ALL USING (auth.role() = 'service_role');

-- Cache
DROP POLICY IF EXISTS "Service Role Full Access On Cache" ON raw_data_cache;
CREATE POLICY "Service Role Full Access On Cache" ON raw_data_cache FOR ALL USING (auth.role() = 'service_role');

-- Detailed Data
DROP POLICY IF EXISTS "Service Role Full Access On Detailed Data" ON detailed_analysis_data;
CREATE POLICY "Service Role Full Access On Detailed Data" ON detailed_analysis_data FOR ALL USING (auth.role() = 'service_role');

-- Async Tasks
DROP POLICY IF EXISTS "Service Role Full Access On Tasks" ON async_tasks;
CREATE POLICY "Service Role Full Access On Tasks" ON async_tasks FOR ALL USING (auth.role() = 'service_role');

-- Config
DROP POLICY IF EXISTS "Service Role Full Access On Config" ON analysis_mode_config;
CREATE POLICY "Service Role Full Access On Config" ON analysis_mode_config FOR ALL USING (auth.role() = 'service_role');

-- Bulk Analysis
DROP POLICY IF EXISTS "Service Role Full Access On Bulk" ON bulk_domain_analysis;
CREATE POLICY "Service Role Full Access On Bulk" ON bulk_domain_analysis FOR ALL USING (auth.role() = 'service_role');

-- Namecheap Domains
DROP POLICY IF EXISTS "Service Role Full Access On Namecheap" ON namecheap_domains;
CREATE POLICY "Service Role Full Access On Namecheap" ON namecheap_domains FOR ALL USING (auth.role() = 'service_role');

-- Secrets
DROP POLICY IF EXISTS "Service role can manage secrets" ON secrets;
CREATE POLICY "Service role can manage secrets" ON secrets FOR ALL USING (auth.role() = 'service_role');

