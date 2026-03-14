-- Create user_resource_usage table
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
CREATE POLICY "Users can view their own usage" 
ON user_resource_usage FOR SELECT 
TO authenticated 
USING (auth.uid() = user_id);

-- Policy: Service role can do everything (insert, select, etc.)
CREATE POLICY "Service role full access" 
ON user_resource_usage FOR ALL 
TO service_role 
USING (true) 
WITH CHECK (true);
