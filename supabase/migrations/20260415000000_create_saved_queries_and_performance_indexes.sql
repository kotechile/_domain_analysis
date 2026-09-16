-- Migration: Create saved_queries table and add performance indexes for advanced search
-- Part of DOM-9: Implement advanced search, filters, and saved queries

-- 1. Create saved_queries table for user-scoped query persistence
CREATE TABLE IF NOT EXISTS saved_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    query_params JSONB NOT NULL DEFAULT '{}',
    is_default BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for fast user-scoped lookups
CREATE INDEX IF NOT EXISTS idx_saved_queries_user_id ON saved_queries(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_queries_user_default ON saved_queries(user_id, is_default) WHERE is_default = true;

-- RLS policies: users can only manage their own saved queries
ALTER TABLE saved_queries ENABLE ROW LEVEL SECURITY;

CREATE POLICY saved_queries_select ON saved_queries
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY saved_queries_insert ON saved_queries
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY saved_queries_update ON saved_queries
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY saved_queries_delete ON saved_queries
    FOR DELETE USING (auth.uid() = user_id);

-- 2. Performance indexes for advanced search filter support
-- These support the new price range and keyword match filters with p95 < 500ms

-- Price range filters on current_bid
CREATE INDEX IF NOT EXISTS idx_auctions_current_bid ON auctions(current_bid) WHERE current_bid IS NOT NULL AND to_delete = false;

-- Composite index for price + offering type queries
CREATE INDEX IF NOT EXISTS idx_auctions_offer_type_bid ON auctions(offer_type, current_bid) WHERE to_delete = false AND current_bid IS NOT NULL;

-- Keyword search: GIN index on domain for trigram/ILIKE acceleration
-- (requires pg_trgm extension)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_auctions_domain_trgm ON auctions USING gin(domain gin_trgm_ops) WHERE to_delete = false;

-- Composite covering index for common marketplace queries (expiration + platform + score)
CREATE INDEX IF NOT EXISTS idx_auctions_marketplace_cover ON auctions(expiration_date, auction_site, score DESC NULLS LAST) WHERE to_delete = false;

-- Support for seller type + statistics combined filter
CREATE INDEX IF NOT EXISTS idx_auctions_offer_type_stats ON auctions(offer_type, has_statistics) WHERE to_delete = false;

-- 3. Add updated_at trigger for saved_queries
CREATE OR REPLACE FUNCTION update_saved_queries_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_saved_queries_updated_at ON saved_queries;
CREATE TRIGGER trg_saved_queries_updated_at
    BEFORE UPDATE ON saved_queries
    FOR EACH ROW
    EXECUTE FUNCTION update_saved_queries_updated_at();