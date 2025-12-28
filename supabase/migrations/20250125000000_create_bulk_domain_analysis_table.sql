-- Create bulk_domain_analysis table for Level 1 (Bulk) Domain Analysis
CREATE TABLE IF NOT EXISTS bulk_domain_analysis (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain_name VARCHAR(255) NOT NULL UNIQUE,
    provider VARCHAR(255),
    backlinks_bulk_page_summary JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_bulk_domain_analysis_domain_name ON bulk_domain_analysis(domain_name);
CREATE INDEX IF NOT EXISTS idx_bulk_domain_analysis_created_at ON bulk_domain_analysis(created_at);
CREATE INDEX IF NOT EXISTS idx_bulk_domain_analysis_summary_null ON bulk_domain_analysis(domain_name) WHERE backlinks_bulk_page_summary IS NULL;
CREATE INDEX IF NOT EXISTS idx_bulk_domain_analysis_summary_gin ON bulk_domain_analysis USING GIN (backlinks_bulk_page_summary);

-- Enable Row Level Security
ALTER TABLE bulk_domain_analysis ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for bulk_domain_analysis table
CREATE POLICY "Public can read bulk domain analysis" ON bulk_domain_analysis
    FOR SELECT USING (true);

CREATE POLICY "Service role can manage bulk domain analysis" ON bulk_domain_analysis
    FOR ALL USING (auth.role() = 'service_role');

-- Create trigger for updated_at on bulk_domain_analysis table
CREATE TRIGGER update_bulk_domain_analysis_updated_at 
    BEFORE UPDATE ON bulk_domain_analysis 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
