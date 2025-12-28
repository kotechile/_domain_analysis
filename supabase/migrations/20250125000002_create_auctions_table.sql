-- Create auctions table for multi-source domain auction data
CREATE TABLE IF NOT EXISTS auctions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain VARCHAR(255) NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE,
    expiration_date TIMESTAMP WITH TIME ZONE NOT NULL,
    auction_site VARCHAR(100) NOT NULL, -- 'namecheap', 'godaddy', 'namesilo', etc.
    ranking INTEGER, -- from scoring service
    score DECIMAL(10,2), -- total_meaning_score
    preferred BOOLEAN DEFAULT FALSE, -- meets threshold
    has_statistics BOOLEAN DEFAULT FALSE, -- has bulk_domain_analysis entry
    source_data JSONB, -- original CSV row data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(domain, auction_site, expiration_date)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_auctions_expiration ON auctions(expiration_date);
CREATE INDEX IF NOT EXISTS idx_auctions_preferred ON auctions(preferred, expiration_date) WHERE preferred = TRUE;
CREATE INDEX IF NOT EXISTS idx_auctions_has_stats ON auctions(has_statistics) WHERE has_statistics = FALSE;
CREATE INDEX IF NOT EXISTS idx_auctions_domain ON auctions(domain);
CREATE INDEX IF NOT EXISTS idx_auctions_auction_site ON auctions(auction_site);
CREATE INDEX IF NOT EXISTS idx_auctions_score ON auctions(score) WHERE score IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_auctions_ranking ON auctions(ranking) WHERE ranking IS NOT NULL;

-- Enable Row Level Security
ALTER TABLE auctions ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for auctions table
CREATE POLICY "Public can read auctions" ON auctions
    FOR SELECT USING (true);

CREATE POLICY "Service role can manage auctions" ON auctions
    FOR ALL USING (auth.role() = 'service_role');

-- Create trigger for updated_at on auctions table
CREATE TRIGGER update_auctions_updated_at 
    BEFORE UPDATE ON auctions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();












