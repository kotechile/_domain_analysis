-- Create namecheap_domains table for Namecheap auction domain data
CREATE TABLE IF NOT EXISTS namecheap_domains (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    url TEXT,
    name VARCHAR(255) NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    price DECIMAL(10,2),
    start_price DECIMAL(10,2),
    renew_price DECIMAL(10,2),
    bid_count INTEGER,
    ahrefs_domain_rating DECIMAL(5,2),
    umbrella_ranking INTEGER,
    cloudflare_ranking INTEGER,
    estibot_value DECIMAL(10,2),
    extensions_taken INTEGER,
    keyword_search_count INTEGER,
    registered_date TIMESTAMP WITH TIME ZONE,
    last_sold_price DECIMAL(10,2),
    last_sold_year INTEGER,
    is_partner_sale BOOLEAN,
    semrush_a_score INTEGER,
    majestic_citation INTEGER,
    ahrefs_backlinks INTEGER,
    semrush_backlinks INTEGER,
    majestic_backlinks INTEGER,
    majestic_trust_flow DECIMAL(5,2),
    go_value DECIMAL(10,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(url),
    UNIQUE(name)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_namecheap_domains_name ON namecheap_domains(name);
CREATE INDEX IF NOT EXISTS idx_namecheap_domains_end_date ON namecheap_domains(end_date);
CREATE INDEX IF NOT EXISTS idx_namecheap_domains_price ON namecheap_domains(price);
CREATE INDEX IF NOT EXISTS idx_namecheap_domains_ahrefs_dr ON namecheap_domains(ahrefs_domain_rating);
CREATE INDEX IF NOT EXISTS idx_namecheap_domains_estibot_value ON namecheap_domains(estibot_value);

-- Enable Row Level Security
ALTER TABLE namecheap_domains ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for namecheap_domains table
CREATE POLICY "Public can read namecheap domains" ON namecheap_domains
    FOR SELECT USING (true);

CREATE POLICY "Service role can manage namecheap domains" ON namecheap_domains
    FOR ALL USING (auth.role() = 'service_role');

-- Create trigger for updated_at on namecheap_domains table
CREATE TRIGGER update_namecheap_domains_updated_at 
    BEFORE UPDATE ON namecheap_domains 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
