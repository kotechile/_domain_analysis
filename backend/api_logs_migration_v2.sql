DROP TABLE IF EXISTS api_usage_logs;

CREATE TABLE api_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    user_action VARCHAR(255) NOT NULL,
    api_service VARCHAR(255) NOT NULL,
    request_id VARCHAR(255),
    cost DECIMAL(10, 4) DEFAULT 0.0000,
    credits_count DECIMAL(10, 4) DEFAULT 0.0000,
    domain VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster querying by user
CREATE INDEX IF NOT EXISTS idx_api_usage_logs_user_id ON api_usage_logs(user_id);

ALTER TABLE api_usage_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Admin manage api_usage_logs" ON api_usage_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
