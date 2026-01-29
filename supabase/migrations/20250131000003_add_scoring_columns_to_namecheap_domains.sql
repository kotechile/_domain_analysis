-- Add scoring columns to namecheap_domains table
-- These columns store the results of domain pre-screening and scoring

ALTER TABLE namecheap_domains
ADD COLUMN IF NOT EXISTS filter_status VARCHAR(10) CHECK (filter_status IN ('PASS', 'FAIL')),
ADD COLUMN IF NOT EXISTS filter_reason TEXT,
ADD COLUMN IF NOT EXISTS total_meaning_score DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS age_score DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS lexical_frequency_score DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS semantic_value_score DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS rank INTEGER;

-- Create indexes for score-based queries
CREATE INDEX IF NOT EXISTS idx_namecheap_domains_filter_status ON namecheap_domains(filter_status);
CREATE INDEX IF NOT EXISTS idx_namecheap_domains_total_meaning_score ON namecheap_domains(total_meaning_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_namecheap_domains_rank ON namecheap_domains(rank);

-- Add comment to explain the columns
COMMENT ON COLUMN namecheap_domains.filter_status IS 'Stage 1 pre-screening result: PASS (passed filtering) or FAIL (failed filtering)';
COMMENT ON COLUMN namecheap_domains.filter_reason IS 'Reason for filter failure (if filter_status = FAIL)';
COMMENT ON COLUMN namecheap_domains.total_meaning_score IS 'Combined score (0-100) from age, lexical frequency, and semantic value';
COMMENT ON COLUMN namecheap_domains.age_score IS 'Age score component (0-100)';
COMMENT ON COLUMN namecheap_domains.lexical_frequency_score IS 'Lexical frequency score component (0-100)';
COMMENT ON COLUMN namecheap_domains.semantic_value_score IS 'Semantic value score component (0-100)';
COMMENT ON COLUMN namecheap_domains.rank IS 'Ranking position among domains that passed filtering (lower is better)';














