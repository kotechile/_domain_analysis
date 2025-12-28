# N8N Auction Workflow Enhancements

## Overview

The Domain Auction Scoring workflow has been enhanced to handle more complex auction data management requirements.

## Changes Made

### 1. Added Current Bid Column

- **Migration**: Created `20251211000001_add_current_bid_to_auctions.sql` to add `current_bid DECIMAL(10,2)` column
- **Extraction**: Updated Python code to extract `current_bid` from CSV columns:
  - Tries: `price`, `Price`, `currentBid`, `current_bid`, `bid`, `Bid`
  - Handles currency symbols ($, USD) and commas
  - Converts to float for database storage

### 2. Backlinks Data Preservation

- **Note**: `backlinks_bulk_page_summary` is stored in `bulk_domain_analysis` table, not `auctions`
- **Preservation**: When updating auctions, the backlinks data in `bulk_domain_analysis` is automatically preserved (it's linked by `domain_name`)
- **No Action Required**: The workflow doesn't need to explicitly preserve it since it's in a separate table

### 3. Smart Upsert Logic

The workflow now handles existing vs new domains intelligently:

**For Existing Domains:**
- Deletes old records for the domain+auction_site combination
- Inserts new record with updated `current_bid` and `expiration_date`
- This handles cases where `expiration_date` changes (which would otherwise create a duplicate due to unique constraint)

**For New Domains:**
- Inserts new record with all data (domain, dates, current_bid, etc.)

### 4. Expired Records Cleanup

- Added "Delete Expired Records" node
- Executes: `DELETE FROM auctions WHERE expiration_date < NOW();`
- Runs after upsert, before scoring
- Removes all auctions that have expired

## Workflow Flow

```
Webhook (auction-scoring)
  ↓
Download CSV from Storage
  ↓
Code in Python (Beta) - Extract domains, dates, current_bid
  ↓
Upsert Domains with Current Bid - Delete old + Insert new
  ↓
Delete Expired Records - Remove expired auctions
  ↓
Execute Scoring Function - Score and rank domains
```

## Database Schema Changes

### New Column: `current_bid`

```sql
ALTER TABLE auctions 
ADD COLUMN IF NOT EXISTS current_bid DECIMAL(10,2);
```

This column stores the current bid amount for each domain auction.

## CSV Column Mapping

The Python code extracts data from CSV using these column name variations:

- **Domain**: `name`, `Name`, `Domain`, `domain`, `url`
- **Start Date**: `startDate`, `Start Date`, `start_date`
- **End Date**: `endDate`, `End Date`, `end_date`, `expirationDate`
- **Current Bid**: `price`, `Price`, `currentBid`, `current_bid`, `bid`, `Bid`

## Important Notes

1. **Unique Constraint**: The auctions table has a unique constraint on `(domain, auction_site, expiration_date)`
   - If `expiration_date` changes for an existing domain, it would create a duplicate
   - Solution: Delete old records for domain+auction_site before inserting new ones

2. **Backlinks Data**: `backlinks_bulk_page_summary` is in `bulk_domain_analysis` table
   - Linked by `domain_name` (matches `auctions.domain`)
   - Automatically preserved when updating auctions
   - No special handling needed in the workflow

3. **Expired Records**: Deleted automatically after each upload
   - Prevents table from growing with expired auctions
   - Keeps data current and relevant

## Testing

To test the workflow:

1. Import the updated JSON into N8N
2. Upload a CSV file with domains, dates, and prices
3. Verify:
   - `current_bid` is populated correctly
   - Existing domains are updated (not duplicated)
   - Expired records are removed
   - Backlinks data remains intact in `bulk_domain_analysis`

## Migration Required

Before using the enhanced workflow, run the migration:

```bash
supabase db push
```

Or manually apply:
```sql
ALTER TABLE auctions ADD COLUMN IF NOT EXISTS current_bid DECIMAL(10,2);
CREATE INDEX IF NOT EXISTS idx_auctions_current_bid ON auctions(current_bid) WHERE current_bid IS NOT NULL;
```









