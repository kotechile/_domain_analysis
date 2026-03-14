-- Create secrets table for secure credential storage
CREATE TABLE IF NOT EXISTS secrets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL UNIQUE,
    credentials JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id),
    updated_by UUID REFERENCES auth.users(id)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_secrets_service_name ON secrets(service_name);
CREATE INDEX IF NOT EXISTS idx_secrets_is_active ON secrets(is_active);

-- Enable Row Level Security
ALTER TABLE secrets ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
-- Only authenticated users can read secrets
CREATE POLICY "Users can read secrets" ON secrets
    FOR SELECT USING (auth.role() = 'authenticated');

-- Only service role can insert/update/delete secrets
CREATE POLICY "Service role can manage secrets" ON secrets
    FOR ALL USING (auth.role() = 'service_role');

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updated_at
CREATE TRIGGER update_secrets_updated_at 
    BEFORE UPDATE ON secrets 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert initial secrets (you'll need to replace these with your actual values)
INSERT INTO secrets (service_name, credentials) VALUES
('dataforseo', '{"login": "your-dataforseo-login", "password": "your-dataforseo-password", "api_url": "your-dataforseo-api-url"}'),
('gemini', '{"api_key": "your-gemini-api-key"}'),
('openai', '{"api_key": "your-openai-api-key"}'),
('wayback_machine', '{"api_url": "http://web.archive.org/cdx/search/cdx"}'),
('google_trends', '{"api_key": "your-google-trends-api-key"}'),
('shareasale', '{"api_key": "your-shareasale-api-key"}'),
('impact', '{"api_key": "your-impact-api-key"}'),
('amazon_associates', '{"tag": "your-amazon-tag"}'),
('cj', '{"api_key": "your-cj-api-key"}'),
('partnerize', '{"api_key": "your-partnerize-api-key"}'),
('reddit', '{"client_id": "your-reddit-client-id", "client_secret": "your-reddit-client-secret"}'),
('twitter', '{"bearer_token": "your-twitter-bearer-token"}'),
('tiktok', '{"api_key": "your-tiktok-api-key"}'),
('surfer_seo', '{"api_key": "your-surfer-seo-api-key"}'),
('frase', '{"api_key": "your-frase-api-key"}'),
('coschedule', '{"api_key": "your-coschedule-api-key"}'),
('google_docs', '{"api_key": "your-google-docs-api-key"}'),
('notion', '{"api_key": "your-notion-api-key"}'),
('wordpress', '{"api_url": "your-wordpress-api-url", "api_key": "your-wordpress-api-key"}'),
('linkup', '{"api_key": "your-linkup-api-key"}')
ON CONFLICT (service_name) DO NOTHING;
