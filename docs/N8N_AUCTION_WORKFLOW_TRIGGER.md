# N8N Auction Workflow Trigger Setup

## Issue
The frontend was uploading CSV files successfully, but the N8N workflow was not being triggered.

## Root Cause
The backend was processing CSV files directly instead of:
1. Storing them in Supabase storage
2. Triggering the N8N workflow to process them

## Solution Implemented

### 1. Added Storage Upload Method
Added `upload_csv_to_storage()` method to `DatabaseService` to upload CSV files to Supabase storage bucket `auction-csvs`.

### 2. Added N8N Auction Scoring Webhook
- Added `N8N_WEBHOOK_URL_AUCTION_SCORING` to config
- Added `trigger_auction_scoring_workflow()` method to `N8NService`

### 3. Updated Upload Endpoint
Modified `/auctions/upload-csv` endpoint to:
1. Upload CSV to Supabase storage
2. Trigger N8N workflow with file path
3. Fallback to direct processing if N8N is not available

## Configuration Required

Add to your `.env` file:

```bash
# N8N Auction Scoring Webhook
N8N_WEBHOOK_URL_AUCTION_SCORING=https://n8n.aichieve.net/webhook/auction-scoring
```

Or if using the same base URL as other N8N webhooks, it will auto-construct from `N8N_WEBHOOK_URL`.

## Workflow

```
Frontend Upload
  ↓
Backend receives CSV
  ↓
Upload to Supabase Storage (bucket: auction-csvs)
  ↓
Trigger N8N Webhook (POST /webhook/auction-scoring)
  ↓
N8N Workflow:
  1. Download CSV from storage
  2. Parse (extract domains, current_bid, dates)
  3. Upsert into auctions table
  4. Delete expired records
  5. Execute scoring function
```

## Testing

1. Ensure N8N workflow is active and webhook URL is correct
2. Upload a CSV file from the frontend
3. Check backend logs for:
   - "CSV uploaded to storage"
   - "N8N workflow triggered successfully"
4. Check N8N workflow execution history
5. Verify data in auctions table

## Fallback Behavior

If N8N is not enabled or webhook fails, the backend will:
- Process the CSV directly (old behavior)
- Return success with status "processed_directly"
- This ensures the system continues to work even if N8N is unavailable









