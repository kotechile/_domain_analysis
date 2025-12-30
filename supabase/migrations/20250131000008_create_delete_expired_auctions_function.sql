-- Create function to delete expired auctions
-- This function deletes all auctions where expiration_date < NOW()
-- Returns the count of deleted records

CREATE OR REPLACE FUNCTION delete_expired_auctions()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_deleted_count INTEGER := 0;
BEGIN
    -- Delete all records where expiration_date is in the past
    DELETE FROM auctions 
    WHERE expiration_date < NOW();
    
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    
    RETURN v_deleted_count;
EXCEPTION WHEN OTHERS THEN
    -- Log error but don't fail - return 0 to indicate no records deleted
    RAISE WARNING 'Failed to delete expired auctions: %', SQLERRM;
    RETURN 0;
END;
$$;

-- Add comment
COMMENT ON FUNCTION delete_expired_auctions() IS 'Deletes all auctions with expiration_date in the past. Returns count of deleted records.';










