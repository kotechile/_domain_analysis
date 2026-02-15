-- Migration to move pricing from code to database

-- 1. Create system_settings table for global config
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert global multiplier
INSERT INTO system_settings (key, value, description)
VALUES ('cost_multiplier', '2.0', 'Global multiplier applied to all base costs')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- 2. Create pricing_rates table
CREATE TABLE IF NOT EXISTS pricing_rates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    resource_type VARCHAR(50) NOT NULL, -- 'llm', 'dataforseo'
    provider VARCHAR(50) NOT NULL,      -- 'openai', 'gemini', 'dataforseo'
    model VARCHAR(50),                  -- 'gpt-4o', 'domain_analytics', etc.
    input_cost DECIMAL(10, 6) NOT NULL, -- Cost per unit (per 1k tokens or per request)
    output_cost DECIMAL(10, 6) DEFAULT 0.0,
    unit_name VARCHAR(20) DEFAULT 'unit', -- 'tokens', 'request'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(resource_type, provider, model)
);

-- 3. Populate initial rates (Base costs)
-- DataForSEO
INSERT INTO pricing_rates (resource_type, provider, model, input_cost, unit_name) VALUES
('dataforseo', 'dataforseo', 'domain_analytics', 0.05, 'request'),
('dataforseo', 'dataforseo', 'backlinks', 0.05, 'request'),
('dataforseo', 'dataforseo', 'keywords', 0.02, 'request');

-- OpenAI
INSERT INTO pricing_rates (resource_type, provider, model, input_cost, output_cost, unit_name) VALUES
('llm', 'openai', 'gpt-4o', 0.005, 0.015, '1k_tokens'),
('llm', 'openai', 'gpt-4-turbo', 0.01, 0.03, '1k_tokens'),
('llm', 'openai', 'gpt-3.5-turbo', 0.0005, 0.0015, '1k_tokens');

-- Gemini
INSERT INTO pricing_rates (resource_type, provider, model, input_cost, output_cost, unit_name) VALUES
('llm', 'gemini', 'gemini-1.5-pro', 0.0035, 0.0105, '1k_tokens'),
('llm', 'gemini', 'gemini-1.5-flash', 0.00035, 0.00105, '1k_tokens');

-- 4. Enable RLS
ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE pricing_rates ENABLE ROW LEVEL SECURITY;

-- Policies: Everyone can read, only service_role can write
CREATE POLICY "Public read settings" ON system_settings FOR SELECT TO authenticated USING (true);
CREATE POLICY "Public read rates" ON pricing_rates FOR SELECT TO authenticated USING (true);

CREATE POLICY "Service role manages settings" ON system_settings FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role manages rates" ON pricing_rates FOR ALL TO service_role USING (true) WITH CHECK (true);
