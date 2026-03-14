-- Create reports table for domain analysis reports
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

-- Create raw_data_cache table for caching API responses
CREATE TABLE IF NOT EXISTS raw_data_cache (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_name VARCHAR(255) NOT NULL,
    api_source VARCHAR(50) NOT NULL,
    json_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(domain_name, api_source)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_reports_domain_name ON reports(domain_name);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at);
CREATE INDEX IF NOT EXISTS idx_raw_data_cache_domain_source ON raw_data_cache(domain_name, api_source);
CREATE INDEX IF NOT EXISTS idx_raw_data_cache_expires_at ON raw_data_cache(expires_at);

-- Enable Row Level Security
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_data_cache ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for reports table
-- Allow public read access to reports
CREATE POLICY "Public can read reports" ON reports
    FOR SELECT USING (true);

-- Allow service role to manage reports
CREATE POLICY "Service role can manage reports" ON reports
    FOR ALL USING (auth.role() = 'service_role');

-- Create RLS policies for raw_data_cache table
-- Allow service role to manage cache
CREATE POLICY "Service role can manage cache" ON raw_data_cache
    FOR ALL USING (auth.role() = 'service_role');

-- Create trigger for updated_at on reports table
CREATE TRIGGER update_reports_updated_at 
    BEFORE UPDATE ON reports 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();








