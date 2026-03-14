-- Migration to implement Credit Tiering System

-- 1. Create action_rates table for fixed action costs
CREATE TABLE IF NOT EXISTS action_rates (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    action_name VARCHAR(100) UNIQUE NOT NULL, -- 'stats_sync', 'ai_domain_summary', 'deep_content_analysis'
    credit_cost DECIMAL(10, 4) NOT NULL,
    unit_amount INTEGER DEFAULT 1,            -- e.g., 1000 for stats_sync
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert the new action costs
INSERT INTO action_rates (action_name, credit_cost, unit_amount, description) VALUES
('stats_sync', 0.08, 1000, 'Credits per 1,000 sites synced'),
('ai_domain_summary', 0.25, 1, 'Credits per AI domain summary report'),
('deep_content_analysis', 1.00, 1, 'Credits per Deep Content Analysis report')
ON CONFLICT (action_name) DO UPDATE SET 
    credit_cost = EXCLUDED.credit_cost,
    unit_amount = EXCLUDED.unit_amount;

-- 2. Create subscription_tiers table
CREATE TABLE IF NOT EXISTS subscription_tiers (
    id VARCHAR(50) PRIMARY KEY, -- 'free', 'pro', 'enterprise'
    name VARCHAR(100) NOT NULL,
    monthly_price DECIMAL(10, 2) NOT NULL,
    included_credits DECIMAL(10, 4) NOT NULL,
    features JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Populate initial tiers
INSERT INTO subscription_tiers (id, name, monthly_price, included_credits, features) VALUES
('free', 'Free Tier', 0.00, 5.0000, '{"max_reports_per_task": 10, "auction_alerts": false}'),
('pro', 'Pro Tier', 29.00, 100.0000, '{"max_reports_per_task": 100, "auction_alerts": true}'),
('enterprise', 'Enterprise', 0.00, 0.0000, '{"custom": true}')
ON CONFLICT (id) DO UPDATE SET 
    monthly_price = EXCLUDED.monthly_price,
    included_credits = EXCLUDED.included_credits,
    features = EXCLUDED.features;

-- 3. Create user_subscriptions table to track user tier
CREATE TABLE IF NOT EXISTS user_subscriptions (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),
    tier_id VARCHAR(50) REFERENCES subscription_tiers(id),
    status VARCHAR(50) DEFAULT 'active',
    current_period_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    current_period_end TIMESTAMP WITH TIME ZONE,
    last_reset_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Enable RLS
ALTER TABLE action_rates ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_tiers ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Public read action rates" ON action_rates FOR SELECT TO authenticated USING (true);
CREATE POLICY "Public read tiers" ON subscription_tiers FOR SELECT TO authenticated USING (true);
CREATE POLICY "Users can view their own subscription" ON user_subscriptions FOR SELECT TO authenticated USING (auth.uid() = user_id);

CREATE POLICY "Service role manages action rates" ON action_rates FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role manages tiers" ON subscription_tiers FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Service role manages user subscriptions" ON user_subscriptions FOR ALL TO service_role USING (true) WITH CHECK (true);
