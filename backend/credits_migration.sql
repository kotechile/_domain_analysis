
-- Create user_credits table
CREATE TABLE IF NOT EXISTS user_credits (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),
    balance DECIMAL(10, 4) DEFAULT 0.0000 NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create credit_transactions table
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    amount DECIMAL(10, 4) NOT NULL, -- Negative for usage, positive for purchases
    transaction_type VARCHAR(50) NOT NULL, -- 'purchase', 'usage', 'adjustment', 'refund'
    reference_id VARCHAR(255), -- Optional reference to external payment ID or usage resource ID
    description TEXT,
    balance_after DECIMAL(10, 4) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON credit_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_created_at ON credit_transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_type ON credit_transactions(transaction_type);

-- Enable RLS
ALTER TABLE user_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;

-- Policies for user_credits
-- Users can view their own balance
CREATE POLICY "Users can view their own credits" 
ON user_credits FOR SELECT 
TO authenticated 
USING (auth.uid() = user_id);

-- Only service role can update balance directly (via API/backend)
CREATE POLICY "Service role manages credits" 
ON user_credits FOR ALL 
TO service_role 
USING (true) 
WITH CHECK (true);

-- Policies for credit_transactions
-- Users can view their transaction history
CREATE POLICY "Users can view their own transactions" 
ON credit_transactions FOR SELECT 
TO authenticated 
USING (auth.uid() = user_id);

-- Only service role can insert transactions
CREATE POLICY "Service role manages transactions" 
ON credit_transactions FOR ALL 
TO service_role 
USING (true) 
WITH CHECK (true);

-- RPC for safe credit deduction
CREATE OR REPLACE FUNCTION deduct_credits(
    p_user_id UUID,
    p_amount DECIMAL,
    p_description TEXT,
    p_reference_id VARCHAR
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
        user_id, amount, transaction_type, reference_id, description, balance_after
    ) VALUES (
        p_user_id, -p_amount, 'usage', p_reference_id, p_description, new_balance
    );

    RETURN jsonb_build_object('success', true, 'new_balance', new_balance);
END;
$$;
