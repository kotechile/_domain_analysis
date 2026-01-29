# Auctions Processed Flag Migration

## Overview
Added a `processed` boolean flag to the `auctions` table to track which records have been scored. This allows processing records in batches without reprocessing the same records.

## Migration Steps

### 1. Apply the Migration

**Option A: Using Supabase Studio (Recommended)**
1. Open your Supabase dashboard
2. Go to SQL Editor
3. Run the migration script: `supabase/migrations/20250125000003_add_processed_flag_to_auctions.sql`

**Option B: Using psql**
```bash
psql -h sbdomain.aichieve.net -U postgres -d postgres -f supabase/migrations/20250125000003_add_processed_flag_to_auctions.sql
```

### 2. Verify Migration
Run this query to verify the column was added:
```sql
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'auctions' AND column_name = 'processed';
```

### 3. Check Existing Data
The migration automatically marks all existing records with scores as processed:
```sql
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE processed = TRUE) as processed_count,
    COUNT(*) FILTER (WHERE processed = FALSE) as unprocessed_count
FROM auctions;
```

## How It Works

1. **New Records**: When you upload a CSV, all new records are inserted with `processed = FALSE`
2. **Processing**: When you click "Process Auctions", it only processes records where `processed = FALSE`
3. **After Scoring**: Records are marked as `processed = TRUE` after scoring is complete
4. **Next Batch**: Click "Process Auctions" again to process the next 10,000 unprocessed records

## Benefits

- **No Reprocessing**: Previously processed records are skipped
- **Incremental Processing**: Process your 800K records in manageable 10K batches
- **Resumable**: If processing stops, you can resume from where you left off
- **Efficient**: Only queries unprocessed records, improving performance

## Notes

- The `processed` flag is set to `TRUE` when a record is scored, regardless of whether it passed or failed filtering
- Rankings are calculated globally across all scored records (not just the current batch)
- Preferred status is recalculated after rankings are assigned





















