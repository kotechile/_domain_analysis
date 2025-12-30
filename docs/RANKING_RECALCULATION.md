# Ranking Recalculation Guide

## Overview

The ranking recalculation function can timeout on very large datasets (100K+ scored records). This guide explains how to handle this.

## Automatic Recalculation

By default, the scoring script:
- **Skips** ranking recalculation during batch processing (to avoid timeouts)
- **Recalculates** rankings once at the end of all processing
- If the final recalculation times out, you can run it manually

## Manual Recalculation

### Option 1: Using API Endpoint

```bash
curl -X POST "http://localhost:8000/api/auctions/recalculate-rankings"
```

### Option 2: Using Python

```python
from services.auction_scoring_service import AuctionScoringService

scoring_service = AuctionScoringService()
result = await scoring_service.recalculate_rankings()
print(result)
```

### Option 3: Direct SQL (if you have database access)

```sql
SELECT recalculate_auction_rankings();
```

## Handling Timeouts

If ranking recalculation times out, you have several options:

### Option 1: Increase PostgreSQL Timeout

If you have database access, increase the statement timeout:

```sql
-- Set timeout to 5 minutes (300 seconds)
SET statement_timeout = '300s';
SELECT recalculate_auction_rankings();
```

### Option 2: Process in Smaller Chunks

You can modify the function to process rankings in chunks, but this requires modifying the SQL function.

### Option 3: Run During Off-Peak Hours

Run the recalculation when the database has less load.

## Current Behavior

- **During Processing**: Rankings are NOT recalculated after each batch (to avoid timeouts)
- **After Processing**: Rankings are recalculated once at the end
- **If Timeout**: The script continues processing, and you can manually recalculate later

## Performance Notes

- **Small datasets** (< 50K scored records): Recalculation is fast (~5-10 seconds)
- **Medium datasets** (50K-100K): Recalculation may take 30-60 seconds
- **Large datasets** (> 100K): Recalculation may timeout (default timeout is usually 30-60 seconds)

## Recommendations

1. **For large datasets**: Let processing complete, then manually recalculate rankings
2. **For production**: Consider running ranking recalculation as a separate scheduled job
3. **For development**: You can increase the timeout temporarily if needed

## Status

Your current dataset has **~100K+ scored records**, which is why recalculation is timing out. This is expected behavior, and the script will continue processing successfully. You can recalculate rankings manually after all processing is complete.














