# Backend Scoring Code Removal

## Overview

All backend scoring functionality has been removed. Scoring is now handled by:
1. **Supabase function** - Basic scoring
2. **N8N Python node** - Complex scoring logic
3. **scoring_config table** - Stores scoring parameters

## Removed Backend Code

### 1. API Endpoint Removed
- **`POST /auctions/process`** - Removed from `backend/src/api/routes/auctions.py`
  - This endpoint processed auctions in batches and performed scoring
  - No longer needed as scoring is handled by Supabase + N8N

### 2. Service Methods Removed

**From `backend/src/services/auctions_service.py`:**
- `process_auctions_batch()` - Batch processing with scoring
- `_recalculate_preferred_with_rankings()` - Re-evaluate preferred status
- `get_auctions_for_scoring()` - Fetch auctions for scoring
- `update_auction_scores()` - Batch update scores
- Removed `BatchScoringService` import and usage

**From `backend/src/services/database.py`:**
- `batch_update_auction_scores()` - Batch update scores in database
- `get_auctions_for_scoring()` - Fetch unprocessed auctions for scoring
- `calculate_rankings_for_scored_auctions()` - Calculate global rankings

### 3. Service File Deleted
- **`backend/src/services/batch_scoring_service.py`** - Entire file deleted
  - Contained all batch scoring logic
  - No longer needed

### 4. Models Removed

**From `backend/src/models/auctions.py`:**
- `AuctionProcessingConfig` - Configuration for batch processing
- `AuctionUpdate` - Model for batch updating scores

## Removed Frontend Code

### 1. API Service (`frontend/src/services/api.tsx`)
- Removed `processAuctions()` method
- Removed `AuctionProcessingConfig` interface
- Removed `AuctionProcessResponse` interface

### 2. Auctions Page (`frontend/src/pages/AuctionsPage.tsx`)
- Removed entire "Process Auctions" card section
- Removed `processMutation` hook
- Removed `handleProcess()` function
- Removed processing config state variables:
  - `scoreThreshold`
  - `rankThreshold`
  - `useBothThresholds`
  - `batchSize`
- Removed `PlayArrowIcon` import (no longer used)

## New Scoring Architecture

Scoring is now handled by:

1. **Supabase Function** (`score_and_rank_auctions`)
   - Performs basic scoring operations
   - Called from N8N workflow

2. **N8N Python Node**
   - Handles complex scoring logic
   - Reads parameters from `scoring_config` table
   - Processes domains and updates scores

3. **scoring_config Table**
   - Stores scoring parameters
   - Configurable thresholds and settings

## Migration Notes

- The `/auctions/process` endpoint no longer exists
- Frontend "Process Auctions" button has been removed
- All scoring is now handled automatically by the N8N workflow after CSV upload
- Scoring parameters are managed in the `scoring_config` table in Supabase

## Testing

After these changes:
1. CSV uploads should trigger N8N workflow
2. N8N workflow should handle scoring via Supabase function + Python node
3. No backend scoring endpoints should be accessible
4. Frontend should not show "Process Auctions" section














