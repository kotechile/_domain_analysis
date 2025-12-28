-- Backfill new columns from existing page_statistics JSONB data
-- This migration extracts data from page_statistics and populates the new columns
-- Only runs if the columns exist (i.e., after the first migration has been applied)

DO $$
DECLARE
    updated_count INTEGER;
    columns_exist BOOLEAN;
BEGIN
    -- Check if columns exist before attempting to update
    SELECT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'auctions' 
        AND column_name = 'backlinks'
    ) INTO columns_exist;
    
    IF columns_exist THEN
        -- Columns exist, proceed with backfill
        UPDATE auctions
        SET 
            backlinks = CASE 
                WHEN page_statistics->>'backlinks' IS NOT NULL 
                THEN (page_statistics->>'backlinks')::INTEGER 
                ELSE NULL 
            END,
            referring_domains = CASE 
                WHEN page_statistics->>'referring_domains' IS NOT NULL 
                THEN (page_statistics->>'referring_domains')::INTEGER 
                ELSE NULL 
            END,
            backlinks_spam_score = CASE 
                WHEN page_statistics->>'backlinks_spam_score' IS NOT NULL 
                THEN (page_statistics->>'backlinks_spam_score')::DECIMAL(5,2) 
                ELSE NULL 
            END,
            first_seen = CASE 
                WHEN page_statistics->>'first_seen' IS NOT NULL 
                THEN (page_statistics->>'first_seen')::TIMESTAMP WITH TIME ZONE 
                ELSE NULL 
            END
        WHERE page_statistics IS NOT NULL;

        -- Log the number of records updated
        SELECT COUNT(*) INTO updated_count
        FROM auctions
        WHERE page_statistics IS NOT NULL;
        
        RAISE NOTICE 'Backfilled page_statistics columns for % records', updated_count;
    ELSE
        -- Columns don't exist yet, skip backfill (will be handled when columns are created)
        RAISE NOTICE 'Columns not found - skipping backfill. Run migration 20250131000001 first.';
    END IF;
END $$;
