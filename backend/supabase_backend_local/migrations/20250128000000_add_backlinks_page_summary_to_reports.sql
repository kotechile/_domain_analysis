-- Add backlinks_page_summary column to reports table
-- This stores the DataForSEO backlinks summary data collected during individual domain analysis

ALTER TABLE reports 
ADD COLUMN IF NOT EXISTS backlinks_page_summary JSONB;

-- Add comment for documentation
COMMENT ON COLUMN reports.backlinks_page_summary IS 'DataForSEO backlinks summary data (backlinks, referring_domains, rank, etc.) collected during individual domain analysis';

