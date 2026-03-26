-- Migration: Add user_id column to api_usage_logs table
-- Run this if your api_usage_logs table was created before the user_id column was added

-- Add user_id column
ALTER TABLE api_usage_logs
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);

-- Create index for faster querying
CREATE INDEX IF NOT EXISTS idx_api_usage_logs_user_id ON api_usage_logs(user_id);

-- Update RLS policies to allow service role to insert with user_id
DROP POLICY IF EXISTS "Admin manage api_usage_logs" ON api_usage_logs;
CREATE POLICY "Admin manage api_usage_logs" ON api_usage_logs FOR ALL TO service_role USING (true) WITH CHECK (true);
