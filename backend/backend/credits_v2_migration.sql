
-- 1. Add dollar_amount to credit_transactions to track actual money spent/equivalent
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS dollar_amount DECIMAL(10, 4) DEFAULT 0.0000;

-- 2. Add last_reset_at to user_credits to manage monthly resets
ALTER TABLE user_credits ADD COLUMN IF NOT EXISTS last_reset_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- 3. Create global_settings table if not exists
CREATE TABLE IF NOT EXISTS global_settings (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Create pricing_plans table for credits per dollar
CREATE TABLE IF NOT EXISTS pricing_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    credits_amount INT NOT NULL,
    price_dollars DECIMAL(10, 2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Create refresh_history table to track 1k batch refreshes
CREATE TABLE IF NOT EXISTS refresh_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    batch_size INT NOT NULL DEFAULT 1000,
    credits_spent INT NOT NULL,
    refreshed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    filters_used JSONB -- Optional: track which filters were active during refresh
);

-- 6. Insert default settings
INSERT INTO global_settings (key, value, description) VALUES
('bulk_refresh_1k_cost', '{"credits": 50}', 'Cost to refresh 1,000 domains metrics (DataForSEO)'),
('force_refresh_1k_cost', '{"credits": 150}', 'Premium cost to bypass cache and force a new 1k pull'),
('individual_deep_dive_cost', '{"credits": 10}', 'Cost to unlock detailed analysis for a single domain')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- 7. Insert default pricing plans
INSERT INTO pricing_plans (name, credits_amount, price_dollars) VALUES
('Starter Pack', 50, 5.00),
('Pro Bundle', 250, 20.00),
('Enterprise Scout', 1000, 75.00)
ON CONFLICT DO NOTHING;

-- 8. Enable RLS for new tables
ALTER TABLE global_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE pricing_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE refresh_history ENABLE ROW LEVEL SECURITY;

-- Select policies
CREATE POLICY "Public read for global_settings" ON global_settings FOR SELECT TO authenticated USING (true);
CREATE POLICY "Public read for pricing_plans" ON pricing_plans FOR SELECT TO authenticated USING (true);
CREATE POLICY "Users can view their own refresh history" ON refresh_history FOR SELECT TO authenticated USING (auth.uid() = user_id);

-- Manage policies (service role)
CREATE POLICY "Admin manage global_settings" ON global_settings FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Admin manage pricing_plans" ON pricing_plans FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "Admin manage refresh_history" ON refresh_history FOR ALL TO service_role USING (true) WITH CHECK (true);

-- 9. Update deduct_credits RPC to optionally accept dollar_amount
CREATE OR REPLACE FUNCTION deduct_credits(
    p_user_id UUID,
    p_amount DECIMAL,
    p_description TEXT,
    p_reference_id VARCHAR,
    p_dollar_amount DECIMAL DEFAULT 0.0000
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    current_balance DECIMAL;
    new_balance DECIMAL;
BEGIN
    -- Lock the user row
    SELECT balance INTO current_balance
    FROM user_credits
    WHERE user_id = p_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'User not found');
    END IF;

    IF current_balance < p_amount THEN
        RETURN jsonb_build_object('success', false, 'error', 'Insufficient credits');
    END IF;

    new_balance := current_balance - p_amount;

    -- Update balance
    UPDATE user_credits
    SET balance = new_balance,
        updated_at = NOW()
    WHERE user_id = p_user_id;

    -- Record transaction
    INSERT INTO credit_transactions (
        user_id, amount, transaction_type, reference_id, description, balance_after, dollar_amount
    ) VALUES (
        p_user_id, -p_amount, 'usage', p_reference_id, p_description, new_balance, p_dollar_amount
    );

    RETURN jsonb_build_object('success', true, 'new_balance', new_balance);
END;
$$;
