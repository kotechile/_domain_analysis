# How to Recalculate Rankings for 276K Records

## Current Status
✅ **All 893,051 records processed successfully!**
✅ **276,381 records have scores**
❌ **Rankings need to be recalculated (timed out due to large dataset)**

## Solution Options

### Option 1: Increase PostgreSQL Timeout (Recommended)

If you have direct database access, increase the timeout and run the function:

```sql
-- Connect to your Supabase database
-- Increase timeout to 5 minutes
SET statement_timeout = '300s';

-- Run the ranking function
SELECT recalculate_auction_rankings();

-- Check results
SELECT 
    COUNT(*) as total_scored,
    COUNT(*) FILTER (WHERE ranking IS NOT NULL) as ranked,
    COUNT(*) FILTER (WHERE preferred = TRUE) as preferred
FROM auctions
WHERE score IS NOT NULL;
```

### Option 2: Use API Endpoint (May Still Timeout)

```bash
curl -X POST "http://localhost:8000/api/auctions/recalculate-rankings"
```

**Note**: This may still timeout if your database timeout is set too low.

### Option 3: Apply Migration and Use Chunked Function

1. Apply the chunked ranking migration:
   ```bash
   # In Supabase SQL Editor, run:
   # supabase/migrations/20250129000002_create_chunked_ranking_function.sql
   ```

2. Then use the chunked function:
   ```sql
   SELECT recalculate_auction_rankings_chunked(50000);
   ```

### Option 4: Manual SQL (Most Reliable for Large Datasets)

Run this SQL directly in your database (it processes in smaller chunks):

```sql
-- Step 1: Clear existing rankings
UPDATE auctions SET ranking = NULL WHERE score IS NOT NULL;

-- Step 2: Calculate rankings (this may take a few minutes)
WITH ranked AS (
    SELECT 
        id,
        ROW_NUMBER() OVER (ORDER BY score DESC NULLS LAST) AS new_ranking
    FROM auctions
    WHERE score IS NOT NULL
)
UPDATE auctions a
SET ranking = r.new_ranking, updated_at = NOW()
FROM ranked r
WHERE a.id = r.id;

-- Step 3: Update preferred flags (adjust thresholds as needed)
WITH config AS (
    SELECT * FROM scoring_config WHERE is_active = TRUE ORDER BY created_at DESC LIMIT 1
)
UPDATE auctions a
SET preferred = 
    CASE 
        WHEN c.score_threshold IS NULL AND c.rank_threshold IS NULL THEN TRUE
        WHEN c.use_both_thresholds THEN
            (c.score_threshold IS NULL OR a.score >= c.score_threshold) AND
            (c.rank_threshold IS NULL OR a.ranking <= c.rank_threshold)
        ELSE
            (c.score_threshold IS NULL OR a.score >= c.score_threshold) OR
            (c.rank_threshold IS NULL OR a.ranking <= c.rank_threshold)
    END,
    updated_at = NOW()
FROM config c
WHERE a.score IS NOT NULL AND a.ranking IS NOT NULL;
```

## Recommended Approach

For 276K records, I recommend **Option 1** (increase timeout + run function) or **Option 4** (manual SQL).

The manual SQL approach is most reliable because:
- You can see progress
- You can adjust if needed
- It's a single transaction
- Works even with default timeouts if run directly

## After Recalculation

Verify the results:

```sql
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE score IS NOT NULL) as scored,
    COUNT(*) FILTER (WHERE ranking IS NOT NULL) as ranked,
    COUNT(*) FILTER (WHERE preferred = TRUE) as preferred,
    MIN(ranking) as min_rank,
    MAX(ranking) as max_rank
FROM auctions;
```

You should see:
- **scored**: 276,381
- **ranked**: 276,381
- **preferred**: Varies based on your config thresholds


















