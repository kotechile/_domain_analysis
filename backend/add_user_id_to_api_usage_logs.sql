-- Migration to add user_id column if it doesn't exist (for existing tables)
-- The table already has: id, endpoint, request_id, cost, credits_count, domain, created_at

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'api_usage_logs' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE api_usage_logs ADD COLUMN user_id UUID REFERENCES auth.users(id);
        CREATE INDEX idx_api_usage_logs_user_id ON api_usage_logs(user_id);
    END IF;
END $$;

-- Ensure RLS policy exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'api_usage_logs' AND policyname = 'Admin manage api_usage_logs'
    ) THEN
        CREATE POLICY "Admin manage api_usage_logs" ON api_usage_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
    END IF;
END $$;
