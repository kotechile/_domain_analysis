-- Create filters table for storing domain marketplace filter settings
CREATE TABLE IF NOT EXISTS filters (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT, -- Optional: for future multi-user support, can be NULL for global defaults
    filter_name VARCHAR(100) DEFAULT 'default',
    
    -- Filter criteria
    preferred BOOLEAN DEFAULT NULL,
    auction_site VARCHAR(50) DEFAULT NULL,
    tld VARCHAR(20) DEFAULT NULL,
    has_statistics BOOLEAN DEFAULT NULL,
    scored BOOLEAN DEFAULT NULL,
    min_rank INTEGER DEFAULT NULL,
    max_rank INTEGER DEFAULT NULL,
    min_score DECIMAL(5,2) DEFAULT NULL,
    max_score DECIMAL(5,2) DEFAULT NULL,
    
    -- Sorting
    sort_by VARCHAR(50) DEFAULT 'expiration_date',
    sort_order VARCHAR(10) DEFAULT 'asc',
    
    -- Pagination
    page_size INTEGER DEFAULT 50,
    
    -- Metadata
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Note: We'll use a partial unique index instead of a constraint to handle NULLs properly
);

-- Drop old constraint if it exists (in case table was already created)
ALTER TABLE filters DROP CONSTRAINT IF EXISTS unique_default_per_user;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_filters_user_id ON filters(user_id);
CREATE INDEX IF NOT EXISTS idx_filters_is_default ON filters(is_default);
CREATE INDEX IF NOT EXISTS idx_filters_filter_name ON filters(filter_name);

-- Create partial unique index to ensure one default filter per user (handles NULL user_id)
-- This works better than a constraint with ON CONFLICT
CREATE UNIQUE INDEX IF NOT EXISTS idx_filters_unique_default_per_user 
ON filters (COALESCE(user_id, ''), is_default) 
WHERE is_default = true;

-- Enable Row Level Security
ALTER TABLE filters ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Public can read filters" ON filters
    FOR SELECT USING (true);

CREATE POLICY "Service role can manage filters" ON filters
    FOR ALL USING (auth.role() = 'service_role');

-- Insert default filter settings
-- Check if default filter already exists before inserting
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM filters 
        WHERE is_default = true 
        AND user_id IS NULL
    ) THEN
        INSERT INTO filters (
            filter_name,
            user_id,
            is_default,
            preferred,
            auction_site,
            tld,
            has_statistics,
            scored,
            min_rank,
            max_rank,
            min_score,
            max_score,
            sort_by,
            sort_order,
            page_size
        ) VALUES (
            'default',
            NULL, -- Global default (no user_id)
            true,
            NULL, -- Show all (preferred and non-preferred)
            NULL, -- Show all auction sites
            NULL, -- Show all TLDs
            NULL, -- Show all (with and without statistics)
            NULL, -- Show all (scored and unscored)
            NULL, -- No minimum rank
            NULL, -- No maximum rank
            NULL, -- No minimum score
            NULL, -- No maximum score
            'expiration_date', -- Sort by expiration date
            'asc', -- Ascending order
            50 -- 50 items per page
        );
    END IF;
END $$;

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_filters_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_filters_updated_at
    BEFORE UPDATE ON filters
    FOR EACH ROW
    EXECUTE FUNCTION update_filters_updated_at();
