-- Check for stuck jobs
SELECT
    job_id,
    filename,
    auction_site,
    status,
    current_stage,
    total_records,
    processed_records,
    inserted_count,
    updated_count,
    error_message,
    started_at,
    updated_at,
    NOW() - updated_at as time_since_update
FROM csv_upload_progress
WHERE status IN ('processing', 'downloading', 'parsing')
ORDER BY started_at DESC;

-- If you see stuck jobs older than 10 minutes, update them to 'failed' or 'completed'
-- Uncomment and run one of these:

-- Option 1: Mark all stuck jobs as failed (recommended for old stuck jobs)
-- UPDATE csv_upload_progress
-- SET status = 'failed',
--     error_message = 'Job stuck - manually cleared',
--     updated_at = NOW()
-- WHERE status IN ('processing', 'downloading', 'parsing')
--   AND updated_at < NOW() - INTERVAL '10 minutes';

-- Option 2: Check specific godaddy job
-- SELECT * FROM csv_upload_progress WHERE filename LIKE '%godaddy_tomorrow%';

-- Option 3: Mark specific stuck job as completed (if you verify it completed)
-- UPDATE csv_upload_progress
-- SET status = 'completed',
--     current_stage = 'completed',
--     progress_percentage = '100.00',
--     completed_at = NOW(),
--     updated_at = NOW()
-- WHERE job_id = '5d1f0b68-64d0-473e-b025-13c5894feae3';
