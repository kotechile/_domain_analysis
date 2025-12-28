-- Create DataForSEO queue table for on-demand user requests
-- This table queues domains for DataForSEO analysis, processing when 100 domains are collected
-- Domains are prioritized by expiration_date (closest to NOW first) and only scored domains (score > 0)

CREATE TABLE IF NOT EXISTS dataforseo_queue (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    expiration_date TIMESTAMP WITH TIME ZONE, -- From auctions table for priority sorting
    score DECIMAL(10,2), -- From auctions table to verify domain is scored
    auction_id UUID, -- Reference to auctions table
    position INTEGER, -- Position in queue (calculated based on expiration_date)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    
    -- Ensure domain is unique in queue (prevent duplicates)
    UNIQUE(domain)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_dataforseo_queue_status ON dataforseo_queue(status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_dataforseo_queue_expiration ON dataforseo_queue(expiration_date) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_dataforseo_queue_domain ON dataforseo_queue(domain);
CREATE INDEX IF NOT EXISTS idx_dataforseo_queue_created ON dataforseo_queue(created_at);

-- Enable Row Level Security
ALTER TABLE dataforseo_queue ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Public can read queue" ON dataforseo_queue
    FOR SELECT USING (true);

CREATE POLICY "Service role can manage queue" ON dataforseo_queue
    FOR ALL USING (auth.role() = 'service_role');

-- Create trigger for updated_at
CREATE TRIGGER update_dataforseo_queue_updated_at 
    BEFORE UPDATE ON dataforseo_queue 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments
COMMENT ON TABLE dataforseo_queue IS 'Queue for user-requested DataForSEO analysis. Processes when 100 domains are queued.';
COMMENT ON COLUMN dataforseo_queue.status IS 'Queue status: pending, processing, completed, failed';
COMMENT ON COLUMN dataforseo_queue.expiration_date IS 'Expiration date from auctions table for priority sorting (closest to NOW first)';
COMMENT ON COLUMN dataforseo_queue.score IS 'Score from auctions table - only scored domains (score > 0) are queued';
COMMENT ON COLUMN dataforseo_queue.position IS 'Position in queue based on expiration_date priority';




