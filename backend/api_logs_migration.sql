
CREATE TABLE IF NOT EXISTS api_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint VARCHAR(255) NOT NULL,
    request_id VARCHAR(255),
    cost DECIMAL(10, 4) DEFAULT 0.0000,
    credits_count DECIMAL(10, 4) DEFAULT 0.0000,
    domain VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE api_usage_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Admin manage api_usage_logs" ON api_usage_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
