-- Function to load CSV data directly into auctions table with Mark & Sweep cleanup support
-- This function processes CSV in chunks and inserts/updates records
-- It now supports chunked mark-and-sweep:
-- 1. If p_chunk_number = 1, it marks ALL records for this site as to_delete = true
-- 2. For every record in the CSV, it sets to_delete = false (upsert)
-- 3. If p_chunk_number = p_total_chunks, it deletes ALL records for this site where to_delete = true

CREATE OR REPLACE FUNCTION load_auctions_from_csv(
    p_csv_content TEXT,
    p_auction_site VARCHAR(100),
    p_chunk_number INTEGER DEFAULT 1,
    p_total_chunks INTEGER DEFAULT 1
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
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
    v_updated_count INTEGER := 0;
    v_skipped_count INTEGER := 0;
    v_total_count INTEGER := 0;
    v_deleted_flagged INTEGER := 0;
    v_batch_size INTEGER := 1000;
    v_batch_count INTEGER := 0;
    v_deleted_expired INTEGER := 0;
    v_header_idx INTEGER;
    v_domain_idx INTEGER := -1;
    v_start_date_idx INTEGER := -1;
    v_expiration_date_idx INTEGER := -1;
    v_price_idx INTEGER := -1;
    v_error_detail TEXT;
    v_error_hint TEXT;
    v_error_context TEXT;
    v_header_line TEXT;
    v_first_newline_pos INTEGER;
    v_data_section TEXT;
    v_line_record RECORD;
    v_record_exists BOOLEAN;
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

    -- MARK PHASE (Only on first chunk)
    -- This sets the to_delete flag for all existing records for this site.
    -- Later records in the CSV will have this flag cleared.
    IF p_chunk_number = 1 THEN
        UPDATE auctions SET to_delete = true 
        WHERE auction_site = p_auction_site;
    END IF;
    
    -- Extract first line (header) - find first newline
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
    
    -- Parse header and find column indices
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
    
    -- Validate we found at least the domain column
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
    
    -- Process each line
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
        v_domain := trim(both '"' from trim(v_row_data[v_domain_idx]));
        v_domain := regexp_replace(v_domain, '^https?://', '', 'gi');
        v_domain := regexp_replace(v_domain, '^www\.', '', 'gi');
        v_domain := split_part(v_domain, '/', 1);
        
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
            v_expiration_date := NOW() + interval '7 days'; 
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
        
        -- Check if record exists
        SELECT EXISTS (
            SELECT 1 FROM auctions 
            WHERE domain = v_domain 
            AND auction_site = p_auction_site 
            AND expiration_date = v_expiration_date
        ) INTO v_record_exists;
        
        -- Upsert into auctions table - CLEAR to_delete flag
        INSERT INTO auctions (
            domain,
            start_date,
            expiration_date,
            auction_site,
            current_bid,
            source_data,
            processed,
            preferred,
            has_statistics,
            to_delete
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
            false,
            false
        )
        ON CONFLICT (domain, auction_site, expiration_date)
        DO UPDATE SET
            start_date = EXCLUDED.start_date,
            expiration_date = EXCLUDED.expiration_date,
            current_bid = EXCLUDED.current_bid,
            source_data = EXCLUDED.source_data,
            to_delete = false, -- Record is still in file, unmark it!
            updated_at = NOW();
        
        IF v_record_exists THEN
            v_updated_count := v_updated_count + 1;
        ELSE
            v_inserted_count := v_inserted_count + 1;
        END IF;
    END LOOP;
    
    -- Cleanup of expired records
    DELETE FROM auctions WHERE expiration_date < NOW();
    GET DIAGNOSTICS v_deleted_expired = ROW_COUNT;

    -- SWEEP PHASE (Only on last chunk)
    -- This deletes any records that were NOT present in any of the chunks.
    IF p_chunk_number = p_total_chunks THEN
        DELETE FROM auctions 
        WHERE auction_site = p_auction_site 
        AND to_delete = true;
        GET DIAGNOSTICS v_deleted_flagged = ROW_COUNT;
    END IF;
    
    RETURN jsonb_build_object(
        'success', true,
        'inserted', v_inserted_count,
        'updated', v_updated_count,
        'skipped', v_skipped_count,
        'deleted_expired', v_deleted_expired,
        'deleted_flagged', v_deleted_flagged,
        'total_processed', v_total_count,
        'auction_site', p_auction_site,
        'chunk', p_chunk_number,
        'total_chunks', p_total_chunks
    );
END;
$$;
