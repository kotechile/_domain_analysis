-- Create scoring_config table to store scoring parameters
CREATE TABLE IF NOT EXISTS scoring_config (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    -- Filtering thresholds
    tier_1_tlds TEXT[] DEFAULT ARRAY['.com', '.net', '.org', '.io', '.ai', '.co'], -- Array of TLDs to allow
    max_domain_length INTEGER DEFAULT 20, -- Maximum length of domain name (without TLD)
    max_numbers INTEGER DEFAULT 2, -- Maximum number of digits in domain name
    -- Scoring weights (must sum to 1.0)
    age_weight DECIMAL(3,2) DEFAULT 0.40,
    lfs_weight DECIMAL(3,2) DEFAULT 0.30, -- Lexical frequency score weight
    sv_weight DECIMAL(3,2) DEFAULT 0.30, -- Semantic value weight
    -- Preferred thresholds
    score_threshold DECIMAL(5,2) DEFAULT NULL, -- Minimum score to mark as preferred
    rank_threshold INTEGER DEFAULT NULL, -- Maximum rank to mark as preferred
    use_both_thresholds BOOLEAN DEFAULT FALSE, -- If true, both thresholds must be met
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for active configs
CREATE INDEX IF NOT EXISTS idx_scoring_config_active ON scoring_config(is_active) WHERE is_active = TRUE;

-- Enable Row Level Security
ALTER TABLE scoring_config ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Public can read scoring_config" ON scoring_config
    FOR SELECT USING (true);

CREATE POLICY "Service role can manage scoring_config" ON scoring_config
    FOR ALL USING (auth.role() = 'service_role');

-- Create trigger for updated_at
CREATE TRIGGER update_scoring_config_updated_at 
    BEFORE UPDATE ON scoring_config 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default configuration
INSERT INTO scoring_config (
    name, 
    description, 
    tier_1_tlds,
    max_domain_length,
    max_numbers,
    age_weight,
    lfs_weight,
    sv_weight,
    is_active
)
VALUES (
    'default',
    'Default scoring configuration with standard weights (age: 40%, lfs: 30%, semantic: 30%)',
    ARRAY['.com', '.net', '.org', '.io', '.ai', '.co'],
    20,
    2,
    0.40,
    0.30,
    0.30,
    TRUE
) ON CONFLICT (name) DO NOTHING;









