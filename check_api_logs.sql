-- Check actual table structure
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'api_usage_logs'
ORDER BY ordinal_position;

-- Check RLS policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies
WHERE tablename = 'api_usage_logs';

-- Check if RLS is enabled
SELECT relname, relrowsecurity, relforcerowsecurity
FROM pg_class
WHERE relname = 'api_usage_logs';

-- Try to see if there are any errors in the logs (check recent entries)
SELECT * FROM api_usage_logs ORDER BY created_at DESC LIMIT 5;
