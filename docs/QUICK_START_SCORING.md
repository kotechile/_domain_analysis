# Quick Start: Auction Scoring System

## Step 1: Apply Migration

Apply the database migration to create the scoring functions and indexes:

```bash
# Option 1: Using Supabase CLI
supabase migration up

# Option 2: Manual SQL
# Run the SQL file in Supabase SQL Editor:
# supabase/migrations/20250129000000_create_optimized_scoring_function.sql
```

## Step 2: Verify Setup

Check that everything is set up correctly:

```sql
-- Check functions exist
SELECT routine_name 
FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND routine_name IN (
    'filter_and_pre_score_auctions',
    'bulk_update_auction_scores',
    'recalculate_auction_rankings'
);

-- Check unprocessed records
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE processed = FALSE) as unprocessed,
    COUNT(*) FILTER (WHERE processed = TRUE) as processed
FROM auctions;
```

## Step 3: Start Processing

### Option A: Using CLI Script (Recommended)

```bash
# Process all unprocessed records continuously
cd backend
python process_auction_scoring.py --batch-size 10000 --continuous

# Or process specific number of batches
python process_auction_scoring.py --batch-size 10000 --batches 10

# Check progress
python process_auction_scoring.py --stats-only
```

### Option B: Using API Endpoint

```bash
# Process one batch
curl -X POST "http://localhost:8000/api/auctions/process-scoring-batch?batch_size=10000"

# Check stats
curl "http://localhost:8000/api/auctions/scoring-stats"

# Recalculate rankings
curl -X POST "http://localhost:8000/api/auctions/recalculate-rankings"
```

### Option C: Using Python Code

```python
from services.auction_scoring_service import AuctionScoringService

scoring_service = AuctionScoringService()

# Process one batch
result = await scoring_service.process_batch(batch_size=10000)
print(result)

# Check stats
stats = await scoring_service.get_processing_stats()
print(stats)
```

## Step 4: Monitor Progress

```bash
# Using CLI
python backend/process_auction_scoring.py --stats-only

# Using API
curl "http://localhost:8000/api/auctions/scoring-stats"
```

## Example Workflow

For processing 1 million records:

```bash
# 1. Check current status
python backend/process_auction_scoring.py --stats-only

# 2. Start processing (will run until all records are processed)
python backend/process_auction_scoring.py --batch-size 10000 --continuous

# 3. Monitor in another terminal
watch -n 30 'python backend/process_auction_scoring.py --stats-only'
```

## Troubleshooting

### No unprocessed records found
- All records may already be processed
- Check: `SELECT COUNT(*) FROM auctions WHERE processed = FALSE;`

### Slow processing
- Reduce batch size: `--batch-size 5000`
- Check database indexes are created
- Check system resources

### Errors
- Check logs for detailed error messages
- Verify scoring config exists: `SELECT * FROM scoring_config WHERE is_active = TRUE;`
- Verify required data files exist for DomainScoringService

## Performance Tips

1. **Batch Size**: Start with 10,000, adjust based on your system
2. **Timing**: Process during off-peak hours for large datasets
3. **Rankings**: Recalculate rankings periodically, not after every batch
4. **Monitoring**: Check stats regularly to track progress

## Next Steps

After scoring is complete:
1. Recalculate rankings globally: `POST /api/auctions/recalculate-rankings`
2. Review scored records: `GET /api/auctions/report?scored=true`
3. Filter by preferred: `GET /api/auctions/report?preferred=true`









