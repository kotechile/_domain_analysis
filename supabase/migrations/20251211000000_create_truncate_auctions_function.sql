-- Create RPC function to truncate auctions table efficiently
-- This avoids URI length issues when deleting large numbers of records via REST API

CREATE OR REPLACE FUNCTION truncate_auctions_table()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    TRUNCATE TABLE auctions RESTART IDENTITY CASCADE;
END;
$$;

-- Grant execute permission to service role
GRANT EXECUTE ON FUNCTION truncate_auctions_table() TO service_role;

-- Also allow authenticated users (for testing)
GRANT EXECUTE ON FUNCTION truncate_auctions_table() TO authenticated;














