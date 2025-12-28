-- Add traffic_data JSONB field to auctions table
-- This field will store DataForSEO Labs API traffic data

ALTER TABLE auctions 
ADD COLUMN IF NOT EXISTS traffic_data JSONB;

-- Create index for efficient queries on traffic_data
CREATE INDEX IF NOT EXISTS idx_auctions_traffic_data 
ON auctions USING GIN (traffic_data) 
WHERE traffic_data IS NOT NULL;

-- Create index for finding domains without traffic_data
CREATE INDEX IF NOT EXISTS idx_auctions_no_traffic_data 
ON auctions(created_at DESC, score DESC) 
WHERE traffic_data IS NULL AND score IS NOT NULL;

-- Add comment
COMMENT ON COLUMN auctions.traffic_data IS 'DataForSEO Labs API traffic data stored as JSONB';

