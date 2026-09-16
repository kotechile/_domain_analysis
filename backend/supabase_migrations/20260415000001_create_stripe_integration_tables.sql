-- Migration: Add Stripe payment integration tables
-- Creates: user_subscriptions, stripe_customers, pricing_plans enhancements

-- 1. Create user_subscriptions table
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tier_id VARCHAR(50) NOT NULL DEFAULT 'free',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- 2. Create stripe_customers table for mapping Stripe customer IDs to users
CREATE TABLE IF NOT EXISTS stripe_customers (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    stripe_customer_id VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Add dollar_amount column to credit_transactions if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'credit_transactions' AND column_name = 'dollar_amount'
    ) THEN
        ALTER TABLE credit_transactions ADD COLUMN dollar_amount DECIMAL(10, 2) DEFAULT 0.0;
    END IF;
END $$;

-- 4. Add last_reset_at to user_credits if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_credits' AND column_name = 'last_reset_at'
    ) THEN
        ALTER TABLE user_credits ADD COLUMN last_reset_at TIMESTAMP WITH TIME ZONE;
    END IF;
END $$;

-- 5. Create indexes
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_stripe_customer ON user_subscriptions(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_stripe_customers_user_id ON stripe_customers(user_id);
CREATE INDEX IF NOT EXISTS idx_stripe_customers_stripe_id ON stripe_customers(stripe_customer_id);

-- 6. Enable RLS
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE stripe_customers ENABLE ROW LEVEL SECURITY;

-- 7. RLS policies
CREATE POLICY "Users can view own subscription" ON user_subscriptions FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Service role manages subscriptions" ON user_subscriptions FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Users can view own stripe customer" ON stripe_customers FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Service role manages stripe customers" ON stripe_customers FOR ALL TO service_role USING (true) WITH CHECK (true);

-- 8. Add subscription_tiers seed data if table exists
INSERT INTO subscription_tiers (id, name, monthly_credits, price_cents, is_active)
VALUES
    ('free', 'Free', 3, 0, true),
    ('pro', 'Pro', 200, 1900, true),
    ('agency', 'Agency', 9999, 4900, true)
ON CONFLICT (id) DO UPDATE SET
    monthly_credits = EXCLUDED.monthly_credits,
    price_cents = EXCLUDED.price_cents,
    is_active = EXCLUDED.is_active;