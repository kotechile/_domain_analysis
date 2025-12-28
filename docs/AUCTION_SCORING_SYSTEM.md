# Auction Scoring System

## Overview

This document describes the hybrid auction scoring system that efficiently processes large volumes of domain auction records using a combination of PostgreSQL (Supabase) and Python.

## Architecture

The system uses a **hybrid approach** that leverages the strengths of both PostgreSQL and Python:

1. **PostgreSQL (Supabase)**: Fast filtering and basic scoring using indexes
2. **Python Backend**: Complex scoring calculations (LFS, semantic value)
3. **Batch Processing**: Processes records in manageable chunks

## Components

### 1. PostgreSQL Functions

#### `filter_and_pre_score_auctions(batch_limit, config_id)`
- **Purpose**: Fast filtering and pre-scoring in the database
- **What it does**:
  - Filters records by TLD, length, special characters, numbers
  - Calculates age score (fast database operation)
  - Returns unprocessed records with filter status
- **Performance**: Uses indexes for fast queries
- **Returns**: Records with `age_score`, `passed_filter`, and `filter_reason`

#### `bulk_update_auction_scores(scores_jsonb)`
- **Purpose**: Bulk update scores from Python backend
- **What it does**:
  - Updates `score`, `lfs_score`, `sv_score` fields
  - Marks records as `processed = TRUE`
- **Performance**: Single transaction for batch updates

#### `recalculate_auction_rankings()`
- **Purpose**: Recalculate global rankings and preferred flags
- **What it does**:
  - Uses window function to assign rankings
  - Updates `preferred` flag based on active config thresholds
- **When to call**: After processing batches or periodically

### 2. Python Service

#### `AuctionScoringService`
Located in `backend/src/services/auction_scoring_service.py`

**Key Methods**:
- `get_unprocessed_batch()`: Fetches batch from Supabase with pre-scoring
- `calculate_complex_scores()`: Calculates LFS and semantic scores
- `update_scores_in_database()`: Bulk updates scores back to database
- `process_batch()`: Main orchestration method
- `get_processing_stats()`: Get statistics about processing status

### 3. API Endpoints

#### `POST /api/auctions/process-scoring-batch`
Process a batch of unprocessed auctions.

**Parameters**:
- `batch_size` (default: 10000): Number of records to process
- `config_id` (optional): Scoring configuration ID
- `recalculate_rankings` (default: true): Recalculate rankings after processing

**Response**:
```json
{
  "success": true,
  "processed_count": 10000,
  "total_fetched": 10000,
  "ranking_stats": {...}
}
```

#### `GET /api/auctions/scoring-stats`
Get statistics about scoring progress.

**Response**:
```json
{
  "unprocessed_count": 500000,
  "processed_count": 300000,
  "scored_count": 250000,
  "total_count": 800000
}
```

#### `POST /api/auctions/recalculate-rankings`
Recalculate global rankings and preferred flags.

### 4. CLI Script

#### `backend/process_auction_scoring.py`

Command-line tool for batch processing.

**Usage**:
```bash
# Process 10 batches of 10,000 records each
python process_auction_scoring.py --batch-size 10000 --batches 10

# Process continuously until all records are done
python process_auction_scoring.py --batch-size 5000 --continuous

# Show statistics only
python process_auction_scoring.py --stats-only
```

## Scoring Logic

### Stage 1: Filtering (PostgreSQL)
Fast database-level filtering:
- ✅ TLD in whitelist (`.com`, `.net`, `.org`, `.io`, `.ai`, `.co`)
- ✅ Domain length ≤ max_length (default: 20)
- ✅ No hyphens or special characters
- ✅ Number count ≤ max_numbers (default: 2)

### Stage 2: Age Score (PostgreSQL)
Calculated in database:
- 10+ years old: 100 points
- 5-10 years old: 50 points
- <5 years old: 20 points
- No registration date: 0 points

### Stage 3: Complex Scores (Python)
Calculated using `DomainScoringService`:
- **LFS (Lexical Frequency Score)**: Based on word frequency rankings
- **Semantic Value Score**: Based on POS tagging and industry keywords

### Stage 4: Total Score
Weighted combination:
```
total_score = (age_score × 0.40) + (lfs_score × 0.30) + (sv_score × 0.30)
```

### Stage 5: Ranking
Global ranking using window function:
```sql
ROW_NUMBER() OVER (ORDER BY score DESC NULLS LAST)
```

### Stage 6: Preferred Flag
Based on active scoring config thresholds:
- `score_threshold`: Minimum score
- `rank_threshold`: Maximum rank
- `use_both_thresholds`: Require both or either

## Performance Optimizations

### Indexes
The system uses several indexes for performance:

```sql
-- Unprocessed records (most important)
CREATE INDEX idx_auctions_processed_created ON auctions(processed, created_at) WHERE processed = FALSE;

-- TLD filtering
CREATE INDEX idx_auctions_domain_tld ON auctions((SPLIT_PART(domain, '.', -1))) WHERE processed = FALSE;

-- Source data (registered_date)
CREATE INDEX idx_auctions_source_data_registered ON auctions USING GIN ((source_data->'registered_date')) WHERE processed = FALSE;

-- Existing indexes
CREATE INDEX idx_auctions_score ON auctions(score) WHERE score IS NOT NULL;
CREATE INDEX idx_auctions_ranking ON auctions(ranking) WHERE ranking IS NOT NULL;
```

### Batch Processing
- Processes records in batches (default: 10,000)
- Uses `LIMIT` to avoid loading entire table
- Marks records as `processed = TRUE` to skip in future batches

### Database-Level Operations
- Filtering happens in PostgreSQL (fast)
- Age scoring happens in PostgreSQL (fast)
- Only complex calculations happen in Python

## Workflow

### Initial Setup
1. Apply migration: `20250129000000_create_optimized_scoring_function.sql`
2. Ensure scoring config exists (default config is created automatically)
3. Verify indexes are created

### Processing Records

**Option 1: API Endpoint**
```bash
curl -X POST "http://localhost:8000/api/auctions/process-scoring-batch?batch_size=10000"
```

**Option 2: CLI Script**
```bash
python backend/process_auction_scoring.py --batch-size 10000 --continuous
```

**Option 3: Python Code**
```python
from services.auction_scoring_service import AuctionScoringService

scoring_service = AuctionScoringService()
result = await scoring_service.process_batch(batch_size=10000)
```

### Monitoring Progress
```bash
# Check stats via API
curl "http://localhost:8000/api/auctions/scoring-stats"

# Or use CLI
python backend/process_auction_scoring.py --stats-only
```

## Configuration

Scoring parameters are stored in the `scoring_config` table:

- `tier_1_tlds`: Allowed TLDs (array)
- `max_domain_length`: Maximum domain name length
- `max_numbers`: Maximum number of digits
- `age_weight`: Weight for age score (default: 0.40)
- `lfs_weight`: Weight for LFS score (default: 0.30)
- `sv_weight`: Weight for semantic value (default: 0.30)
- `score_threshold`: Minimum score for preferred flag
- `rank_threshold`: Maximum rank for preferred flag
- `use_both_thresholds`: Require both thresholds

## Best Practices

1. **Process in Batches**: Don't try to process all records at once
2. **Monitor Progress**: Check stats regularly
3. **Recalculate Rankings**: Call after processing large batches
4. **Use Appropriate Batch Size**: 10,000 is a good default, adjust based on your system
5. **Run During Off-Peak**: For large datasets, run during low-traffic periods

## Troubleshooting

### Slow Processing
- Check if indexes are created
- Reduce batch size
- Check database connection pool settings

### Memory Issues
- Reduce batch size
- Process in smaller chunks

### Missing Scores
- Check if `DomainScoringService` has required data files
- Verify scoring config is active
- Check logs for errors

## Migration

To apply the scoring system:

1. **Apply Migration**:
   ```bash
   # Using Supabase CLI
   supabase migration up
   
   # Or manually in SQL Editor
   # Run: supabase/migrations/20250129000000_create_optimized_scoring_function.sql
   ```

2. **Verify**:
   ```sql
   -- Check functions exist
   SELECT routine_name 
   FROM information_schema.routines 
   WHERE routine_schema = 'public' 
   AND routine_name LIKE '%auction%';
   
   -- Check indexes
   SELECT indexname 
   FROM pg_indexes 
   WHERE tablename = 'auctions' 
   AND indexname LIKE '%processed%';
   ```

3. **Test**:
   ```bash
   python backend/process_auction_scoring.py --batch-size 100 --stats-only
   ```

## Example: Processing 1 Million Records

```bash
# Process in batches of 10,000
# This will process ~100 batches
python backend/process_auction_scoring.py --batch-size 10000 --continuous

# Or process 10 batches at a time
for i in {1..10}; do
  python backend/process_auction_scoring.py --batch-size 10000 --batches 10
  echo "Completed iteration $i"
  sleep 60  # Wait 1 minute between iterations
done
```

## Performance Expectations

- **Filtering**: ~1-5ms per 10,000 records (PostgreSQL)
- **Complex Scoring**: ~10-30 seconds per 10,000 records (Python)
- **Database Update**: ~1-2 seconds per 10,000 records
- **Total**: ~15-40 seconds per 10,000 records

For 1 million records:
- Estimated time: ~25-70 minutes
- Recommended: Process in batches over multiple sessions









