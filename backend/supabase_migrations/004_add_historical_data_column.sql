-- Add historical_data column to reports table
ALTER TABLE reports 
ADD COLUMN IF NOT EXISTS historical_data JSONB;

-- Comment on the column
COMMENT ON COLUMN reports.historical_data IS 'Historical SEO ranking and traffic analytics data over time';
