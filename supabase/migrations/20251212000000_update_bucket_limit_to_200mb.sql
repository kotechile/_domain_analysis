-- Update auction-csvs bucket file size limit to 200MB
-- This migration updates the existing bucket configuration

UPDATE storage.buckets
SET file_size_limit = 209715200  -- 200MB (209715200 bytes)
WHERE id = 'auction-csvs';

-- Verify the update
DO $$
DECLARE
    updated_limit BIGINT;
BEGIN
    SELECT file_size_limit INTO updated_limit
    FROM storage.buckets
    WHERE id = 'auction-csvs';
    
    IF updated_limit = 209715200 THEN
        RAISE NOTICE 'Bucket file_size_limit successfully updated to 200MB';
    ELSE
        RAISE WARNING 'Bucket file_size_limit update may have failed. Current limit: % bytes', updated_limit;
    END IF;
END $$;














