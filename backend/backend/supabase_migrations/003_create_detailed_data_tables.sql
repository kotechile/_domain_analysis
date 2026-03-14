-- Create detailed analysis data table for storing detailed data (backlinks, keywords, referring domains)
CREATE TABLE IF NOT EXISTS detailed_analysis_data (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_name VARCHAR(255) NOT NULL,
    data_type VARCHAR(50) NOT NULL, -- 'backlinks', 'keywords', 'referring_domains'
    json_data JSONB NOT NULL,
    task_id VARCHAR(255), -- DataForSEO task ID for reference
    data_source VARCHAR(50) DEFAULT 'dataforseo',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(domain_name, data_type)
);

-- Create async task tracking table
CREATE TABLE IF NOT EXISTS async_tasks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_name VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL UNIQUE,
    task_type VARCHAR(50) NOT NULL, -- 'backlinks', 'keywords', 'referring_domains'
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

-- Create analysis mode configuration table
CREATE TABLE IF NOT EXISTS analysis_mode_config (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_name VARCHAR(255), -- NULL for global config
    mode_preference VARCHAR(20) DEFAULT 'dual', -- 'legacy', 'async', 'dual'
    async_enabled BOOLEAN DEFAULT true,
    cache_ttl_hours INTEGER DEFAULT 24,
    manual_refresh_enabled BOOLEAN DEFAULT true,
    progress_indicators_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Update reports table with new fields
ALTER TABLE reports ADD COLUMN IF NOT EXISTS detailed_data_available JSONB DEFAULT '{}';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS analysis_phase VARCHAR(50) DEFAULT 'essential';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS analysis_mode VARCHAR(20) DEFAULT 'legacy';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS progress_data JSONB;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_detailed_data_domain_type ON detailed_analysis_data(domain_name, data_type);
CREATE INDEX IF NOT EXISTS idx_detailed_data_expires_at ON detailed_analysis_data(expires_at);
CREATE INDEX IF NOT EXISTS idx_detailed_data_jsonb_gin ON detailed_analysis_data USING GIN (json_data);

CREATE INDEX IF NOT EXISTS idx_async_tasks_domain_type ON async_tasks(domain_name, task_type);
CREATE INDEX IF NOT EXISTS idx_async_tasks_status ON async_tasks(status);
CREATE INDEX IF NOT EXISTS idx_async_tasks_task_id ON async_tasks(task_id);

CREATE INDEX IF NOT EXISTS idx_analysis_mode_config_domain ON analysis_mode_config(domain_name);
CREATE INDEX IF NOT EXISTS idx_analysis_mode_config_global ON analysis_mode_config(domain_name) WHERE domain_name IS NULL;

CREATE INDEX IF NOT EXISTS idx_reports_analysis_phase ON reports(analysis_phase);
CREATE INDEX IF NOT EXISTS idx_reports_analysis_mode ON reports(analysis_mode);
CREATE INDEX IF NOT EXISTS idx_reports_llm_analysis_gin ON reports USING GIN (llm_analysis);

-- Enable Row Level Security
ALTER TABLE detailed_analysis_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE async_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_mode_config ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for detailed_analysis_data
CREATE POLICY "Public can read detailed data" ON detailed_analysis_data 
FOR SELECT USING (true);

CREATE POLICY "Service role can manage detailed data" ON detailed_analysis_data 
FOR ALL USING (auth.role() = 'service_role');

-- Create RLS policies for async_tasks
CREATE POLICY "Service role can manage async tasks" ON async_tasks 
FOR ALL USING (auth.role() = 'service_role');

-- Create RLS policies for analysis_mode_config
CREATE POLICY "Public can read mode config" ON analysis_mode_config 
FOR SELECT USING (true);

CREATE POLICY "Service role can manage mode config" ON analysis_mode_config 
FOR ALL USING (auth.role() = 'service_role');

-- Add check constraints
ALTER TABLE detailed_analysis_data ADD CONSTRAINT chk_data_type 
CHECK (data_type IN ('backlinks', 'keywords', 'referring_domains'));

ALTER TABLE async_tasks ADD CONSTRAINT chk_task_type 
CHECK (task_type IN ('backlinks', 'keywords', 'referring_domains'));

ALTER TABLE async_tasks ADD CONSTRAINT chk_status 
CHECK (status IN ('pending', 'processing', 'completed', 'failed'));

ALTER TABLE analysis_mode_config ADD CONSTRAINT chk_mode_preference 
CHECK (mode_preference IN ('legacy', 'async', 'dual'));

ALTER TABLE analysis_mode_config ADD CONSTRAINT chk_cache_ttl 
CHECK (cache_ttl_hours >= 1 AND cache_ttl_hours <= 168);

ALTER TABLE reports ADD CONSTRAINT chk_analysis_phase 
CHECK (analysis_phase IN ('essential', 'detailed', 'ai_analysis', 'completed'));

ALTER TABLE reports ADD CONSTRAINT chk_analysis_mode 
CHECK (analysis_mode IN ('legacy', 'async', 'dual'));

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updated_at on analysis_mode_config
CREATE TRIGGER update_analysis_mode_config_updated_at 
    BEFORE UPDATE ON analysis_mode_config 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default global configuration
INSERT INTO analysis_mode_config (domain_name, mode_preference, async_enabled, cache_ttl_hours, manual_refresh_enabled, progress_indicators_enabled)
VALUES (NULL, 'dual', true, 24, true, true)
ON CONFLICT DO NOTHING;





