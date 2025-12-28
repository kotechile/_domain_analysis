-- Create storage bucket for auction CSV files
-- This migration creates the 'auction-csvs' bucket with appropriate RLS policies

-- Create the bucket (if it doesn't exist)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'auction-csvs',
  'auction-csvs',
  false, -- Set to true if you want public access, false for authenticated access only
  104857600, -- 100MB file size limit (adjust as needed)
  ARRAY['text/csv', 'application/csv', 'text/plain'] -- Allowed MIME types
)
ON CONFLICT (id) DO NOTHING;

-- Enable Row Level Security on storage.objects for this bucket
-- RLS is automatically enabled, but we'll create policies

-- Policy: Allow service role to upload files
CREATE POLICY "Service role can upload auction CSVs"
ON storage.objects
FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'auction-csvs');

-- Policy: Allow service role to read files
CREATE POLICY "Service role can read auction CSVs"
ON storage.objects
FOR SELECT
TO service_role
USING (bucket_id = 'auction-csvs');

-- Policy: Allow service role to delete files
CREATE POLICY "Service role can delete auction CSVs"
ON storage.objects
FOR DELETE
TO service_role
USING (bucket_id = 'auction-csvs');

-- Policy: Allow service role to update files
CREATE POLICY "Service role can update auction CSVs"
ON storage.objects
FOR UPDATE
TO service_role
USING (bucket_id = 'auction-csvs');

-- Optional: If you want authenticated users to also access files
-- Uncomment these policies if needed:

-- Policy: Allow authenticated users to read files
-- CREATE POLICY "Authenticated users can read auction CSVs"
-- ON storage.objects
-- FOR SELECT
-- TO authenticated
-- USING (bucket_id = 'auction-csvs');

-- Policy: Allow authenticated users to upload files
-- CREATE POLICY "Authenticated users can upload auction CSVs"
-- ON storage.objects
-- FOR INSERT
-- TO authenticated
-- WITH CHECK (bucket_id = 'auction-csvs');

-- Note: The service_role policies above should be sufficient for backend operations
-- since your backend uses the service role key for Supabase operations.
