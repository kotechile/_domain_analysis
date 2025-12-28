-- Create staging table for CSV uploads
-- This table is used to temporarily store CSV data before merging into auctions table
-- The staging table is optimized for bulk inserts and can be truncated between uploads

CREATE TABLE IF NOT EXISTS auctions_staging (
    domain VARCHAR(255) NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE,
    expiration_date TIMESTAMP WITH TIME ZONE NOT NULL,
    auction_site VARCHAR(100) NOT NULL,
    current_bid DECIMAL(10,2),
    source_data JSONB,
    processed BOOLEAN DEFAULT false,
    preferred BOOLEAN DEFAULT false,
    has_statistics BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster lookups during merge
CREATE INDEX IF NOT EXISTS idx_auctions_staging_domain_site_exp ON auctions_staging(domain, auction_site, expiration_date);
CREATE INDEX IF NOT EXISTS idx_auctions_staging_auction_site ON auctions_staging(auction_site);

-- Function to merge staging data into auctions table
-- This efficiently handles inserts and updates in a single operation
CREATE OR REPLACE FUNCTION merge_auctions_from_staging(
    p_auction_site VARCHAR(100)
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_inserted_count INTEGER := 0;
    v_updated_count INTEGER := 0;
    v_skipped_count INTEGER := 0;
    v_deleted_expired INTEGER := 0;
    v_total_staging INTEGER := 0;
BEGIN
    -- Count records in staging
    SELECT COUNT(*) INTO v_total_staging
    FROM auctions_staging
    WHERE auction_site = p_auction_site;
    
    IF v_total_staging = 0 THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'No records found in staging table for auction_site: ' || p_auction_site
        );
    END IF;
    
    -- Merge staging into auctions using INSERT ... ON CONFLICT
    -- This is much faster than individual upserts
    WITH merged AS (
        INSERT INTO auctions (
            domain,
            start_date,
            expiration_date,
            auction_site,
            current_bid,
            source_data,
            processed,
            preferred,
            has_statistics
        )
        SELECT 
            domain,
            start_date,
            expiration_date,
            auction_site,
            current_bid,
            source_data,
            processed,
            preferred,
            has_statistics
        FROM auctions_staging
        WHERE auction_site = p_auction_site
        ON CONFLICT (domain, auction_site, expiration_date)
        DO UPDATE SET
            start_date = EXCLUDED.start_date,
            expiration_date = EXCLUDED.expiration_date,
            current_bid = EXCLUDED.current_bid,
            source_data = EXCLUDED.source_data,
            updated_at = NOW()
        RETURNING 
            CASE WHEN xmax = 0 THEN 'inserted' ELSE 'updated' END as action
    ),
    action_counts AS (
        SELECT 
            COUNT(*) FILTER (WHERE action = 'inserted') as inserted,
            COUNT(*) FILTER (WHERE action = 'updated') as updated
        FROM merged
    )
    SELECT 
        inserted, updated
    INTO 
        v_inserted_count, v_updated_count
    FROM action_counts;
    
    -- Count skipped (if any validation issues)
    v_skipped_count := v_total_staging - v_inserted_count - v_updated_count;
    
    -- Delete expired records from auctions table
    DELETE FROM auctions WHERE expiration_date < NOW();
    GET DIAGNOSTICS v_deleted_expired = ROW_COUNT;
    
    -- Truncate staging table for this auction_site (cleanup)
    DELETE FROM auctions_staging WHERE auction_site = p_auction_site;
    
    RETURN jsonb_build_object(
        'success', true,
        'inserted', v_inserted_count,
        'updated', v_updated_count,
        'skipped', v_skipped_count,
        'deleted_expired', v_deleted_expired,
        'total_processed', v_total_staging,
        'auction_site', p_auction_site
    );
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_detail', PG_EXCEPTION_DETAIL,
        'total_processed', v_total_staging
    );
END;
$$;

-- Function to load CSV into staging table
-- This is optimized for bulk loading using COPY-like operations
CREATE OR REPLACE FUNCTION load_csv_to_staging(
    p_csv_content TEXT,
    p_auction_site VARCHAR(100)
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_line TEXT;
    v_header TEXT[];
    v_row_data TEXT[];
    v_domain VARCHAR(255);
    v_start_date TIMESTAMP WITH TIME ZONE;
    v_expiration_date TIMESTAMP WITH TIME ZONE;
    v_current_bid DECIMAL(10,2);
    v_source_data JSONB;
    v_inserted_count INTEGER := 0;
    v_skipped_count INTEGER := 0;
    v_total_count INTEGER := 0;
    v_header_idx INTEGER;
    v_domain_idx INTEGER := -1;
    v_start_date_idx INTEGER := -1;
    v_expiration_date_idx INTEGER := -1;
    v_price_idx INTEGER := -1;
    v_header_line TEXT;
    v_first_newline_pos INTEGER;
    v_data_section TEXT;
    v_line_record RECORD;
    header_col TEXT;
    header_name TEXT;
    row_value TEXT;
BEGIN
    -- Validate input
    IF p_csv_content IS NULL OR length(trim(p_csv_content)) = 0 THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'CSV content is empty or null'
        );
    END IF;
    
    -- Clear staging table for this auction_site first
    DELETE FROM auctions_staging WHERE auction_site = p_auction_site;
    
    -- Extract header
    v_first_newline_pos := position(E'\n' IN p_csv_content);
    IF v_first_newline_pos = 0 THEN
        v_first_newline_pos := position(E'\r\n' IN p_csv_content);
        IF v_first_newline_pos > 0 THEN
            v_header_line := substring(p_csv_content FROM 1 FOR v_first_newline_pos - 1);
        ELSE
            RETURN jsonb_build_object(
                'success', false,
                'error', 'CSV file has no newlines - invalid format'
            );
        END IF;
    ELSE
        v_header_line := substring(p_csv_content FROM 1 FOR v_first_newline_pos - 1);
    END IF;
    
    -- Parse header
    v_header := string_to_array(v_header_line, ',');
    
    FOR v_header_idx IN 1..array_length(v_header, 1) LOOP
        header_col := trim(both '"' from trim(v_header[v_header_idx]));
        
        IF lower(header_col) IN ('name', 'domain', 'url') THEN
            v_domain_idx := v_header_idx;
        ELSIF lower(header_col) IN ('startdate', 'start_date', 'start date') THEN
            v_start_date_idx := v_header_idx;
        ELSIF lower(header_col) IN ('enddate', 'end_date', 'end date', 'expirationdate', 'expiration_date') THEN
            v_expiration_date_idx := v_header_idx;
        ELSIF lower(header_col) IN ('price', 'currentbid', 'current_bid', 'bid', 'current bid') THEN
            v_price_idx := v_header_idx;
        END IF;
    END LOOP;
    
    IF v_domain_idx = -1 THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'CSV header does not contain a domain column'
        );
    END IF;
    
    -- Extract data section
    IF v_first_newline_pos > 0 THEN
        v_data_section := substring(p_csv_content FROM v_first_newline_pos + 1);
    ELSE
        v_data_section := '';
    END IF;
    
    -- Process each line and insert into staging
    FOR v_line_record IN 
        SELECT trim(line) as line_text
        FROM regexp_split_to_table(v_data_section, E'\r?\n') as line
        WHERE trim(line) != ''
    LOOP
        v_line := v_line_record.line_text;
        v_total_count := v_total_count + 1;
        
        v_row_data := string_to_array(v_line, ',');
        
        IF array_length(v_row_data, 1) < array_length(v_header, 1) THEN
            v_skipped_count := v_skipped_count + 1;
            CONTINUE;
        END IF;
        
        -- Extract domain
        IF v_domain_idx > 0 AND v_domain_idx <= array_length(v_row_data, 1) THEN
            v_domain := trim(both '"' from trim(v_row_data[v_domain_idx]));
            v_domain := regexp_replace(v_domain, '^https?://', '', 'gi');
            v_domain := regexp_replace(v_domain, '^www\.', '', 'gi');
            v_domain := split_part(v_domain, '/', 1);
        ELSE
            v_domain := NULL;
        END IF;
        
        IF v_domain IS NULL OR v_domain = '' THEN
            v_skipped_count := v_skipped_count + 1;
            CONTINUE;
        END IF;
        
        -- Extract dates
        v_start_date := NULL;
        IF v_start_date_idx > 0 AND v_start_date_idx <= array_length(v_row_data, 1) THEN
            BEGIN
                v_start_date := trim(both '"' from trim(v_row_data[v_start_date_idx]))::TIMESTAMP WITH TIME ZONE;
            EXCEPTION WHEN OTHERS THEN
                v_start_date := NULL;
            END;
        END IF;
        
        v_expiration_date := NULL;
        IF v_expiration_date_idx > 0 AND v_expiration_date_idx <= array_length(v_row_data, 1) THEN
            BEGIN
                v_expiration_date := trim(both '"' from trim(v_row_data[v_expiration_date_idx]))::TIMESTAMP WITH TIME ZONE;
            EXCEPTION WHEN OTHERS THEN
                v_expiration_date := NULL;
            END;
        END IF;
        
        IF v_expiration_date IS NULL THEN
            v_expiration_date := NOW();
        END IF;
        
        -- Extract current_bid
        v_current_bid := NULL;
        IF v_price_idx > 0 AND v_price_idx <= array_length(v_row_data, 1) THEN
            BEGIN
                v_current_bid := regexp_replace(trim(both '"' from trim(v_row_data[v_price_idx])), '[^0-9.]', '', 'g')::DECIMAL(10,2);
            EXCEPTION WHEN OTHERS THEN
                v_current_bid := NULL;
            END;
        END IF;
        
        -- Build source_data JSONB
        v_source_data := '{}'::JSONB;
        FOR v_header_idx IN 1..array_length(v_header, 1) LOOP
            IF v_header_idx <= array_length(v_row_data, 1) THEN
                header_name := trim(both '"' from trim(v_header[v_header_idx]));
                row_value := trim(both '"' from trim(v_row_data[v_header_idx]));
                v_source_data := v_source_data || jsonb_build_object(header_name, row_value);
            END IF;
        END LOOP;
        
        -- Insert into staging (no conflict check - staging is append-only)
        INSERT INTO auctions_staging (
            domain,
            start_date,
            expiration_date,
            auction_site,
            current_bid,
            source_data,
            processed,
            preferred,
            has_statistics
        )
        VALUES (
            v_domain,
            v_start_date,
            v_expiration_date,
            p_auction_site,
            v_current_bid,
            v_source_data,
            false,
            false,
            false
        );
        
        v_inserted_count := v_inserted_count + 1;
        
        -- Commit in batches to avoid memory issues
        IF v_inserted_count % 10000 = 0 THEN
            -- Progress checkpoint (though in a function, commits happen at end)
            NULL;
        END IF;
    END LOOP;
    
    RETURN jsonb_build_object(
        'success', true,
        'inserted', v_inserted_count,
        'skipped', v_skipped_count,
        'total_processed', v_total_count,
        'auction_site', p_auction_site
    );
EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object(
        'success', false,
        'error', SQLERRM,
        'error_detail', PG_EXCEPTION_DETAIL,
        'total_processed', v_total_count,
        'inserted', v_inserted_count,
        'skipped', v_skipped_count
    );
END;
$$;
