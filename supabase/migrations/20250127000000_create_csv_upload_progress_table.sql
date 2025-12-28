-- Create table to track CSV upload progress
CREATE TABLE IF NOT EXISTS csv_upload_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id VARCHAR(255) UNIQUE NOT NULL,
    filename VARCHAR(500) NOT NULL,
    auction_site VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, parsing, processing, completed, failed
    total_records INTEGER DEFAULT 0,
    processed_records INTEGER DEFAULT 0,
    inserted_count INTEGER DEFAULT 0,
    updated_count INTEGER DEFAULT 0,
    skipped_count INTEGER DEFAULT 0,
    deleted_expired_count INTEGER DEFAULT 0,
    current_stage VARCHAR(100), -- parsing, converting, upserting, deleting_expired
    progress_percentage DECIMAL(5,2) DEFAULT 0.00,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_csv_upload_progress_job_id ON csv_upload_progress(job_id);
CREATE INDEX IF NOT EXISTS idx_csv_upload_progress_status ON csv_upload_progress(status);
CREATE INDEX IF NOT EXISTS idx_csv_upload_progress_created_at ON csv_upload_progress(created_at DESC);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_csv_upload_progress_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
CREATE TRIGGER update_csv_upload_progress_timestamp
    BEFORE UPDATE ON csv_upload_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_csv_upload_progress_updated_at();

-- Function to calculate progress percentage
CREATE OR REPLACE FUNCTION calculate_progress_percentage(
    processed INTEGER,
    total INTEGER
)
RETURNS DECIMAL(5,2) AS $$
BEGIN
    IF total = 0 THEN
        RETURN 0.00;
    END IF;
    RETURN LEAST(100.00, ROUND((processed::DECIMAL / total::DECIMAL) * 100.00, 2));
END;
$$ LANGUAGE plpgsql;
