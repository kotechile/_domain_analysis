# Filters Table Migration Plan

## Overview
This document describes the migration plan for creating the `filters` table in Supabase to store domain marketplace filter settings.

## Migration File
- **File**: `supabase/migrations/20250131000000_create_filters_table.sql`
- **Purpose**: Create the `filters` table with default values for storing filter preferences

## Table Structure

### Fields
- `id` (UUID, Primary Key) - Unique identifier
- `user_id` (TEXT, Optional) - For future multi-user support (NULL for global defaults)
- `filter_name` (VARCHAR(100)) - Name of the filter preset (default: 'default')
- `preferred` (BOOLEAN, Optional) - Filter by preferred status
- `auction_site` (VARCHAR(50), Optional) - Filter by auction site
- `tld` (VARCHAR(20), Optional) - Filter by TLD extension
- `has_statistics` (BOOLEAN, Optional) - Filter by has_statistics flag
- `scored` (BOOLEAN, Optional) - Filter by scored status
- `min_rank` (INTEGER, Optional) - Minimum ranking filter
- `max_rank` (INTEGER, Optional) - Maximum ranking filter
- `min_score` (DECIMAL(5,2), Optional) - Minimum score filter
- `max_score` (DECIMAL(5,2), Optional) - Maximum score filter
- `sort_by` (VARCHAR(50)) - Field to sort by (default: 'expiration_date')
- `sort_order` (VARCHAR(10)) - Sort order 'asc' or 'desc' (default: 'asc')
- `page_size` (INTEGER) - Number of items per page (default: 50)
- `is_default` (BOOLEAN) - Whether this is the default filter (default: false)
- `created_at` (TIMESTAMP) - Creation timestamp
- `updated_at` (TIMESTAMP) - Last update timestamp

### Constraints
- Unique constraint on `(user_id, is_default)` to ensure one default filter per user
- Indexes on `user_id`, `is_default`, and `filter_name` for performance

### Default Values
The migration inserts a default filter with:
- All filter criteria set to NULL (show all)
- Sort by `expiration_date` ascending
- Page size of 50 items

## Row Level Security (RLS)
- Public read access (anyone can read filters)
- Service role can manage filters (for API operations)

## How to Apply

### Option 1: Via Supabase Dashboard
1. Open Supabase Dashboard
2. Navigate to SQL Editor
3. Copy and paste the contents of `20250131000000_create_filters_table.sql`
4. Execute the SQL

### Option 2: Via Supabase CLI
```bash
cd supabase
supabase db push
```

### Option 3: Manual Application
Run the SQL file directly in your Supabase database using psql or your preferred database client.

## API Endpoints

### GET `/api/v1/filters`
Retrieves filter settings (defaults to global filters if no user_id provided)

**Query Parameters:**
- `user_id` (optional) - User ID for user-specific filters

**Response:**
```json
{
  "success": true,
  "filter": {
    "id": "uuid",
    "preferred": null,
    "auction_site": null,
    "tld": null,
    "has_statistics": null,
    "scored": null,
    "min_rank": null,
    "max_rank": null,
    "min_score": null,
    "max_score": null,
    "sort_by": "expiration_date",
    "sort_order": "asc",
    "page_size": 50,
    "filter_name": "default"
  }
}
```

### PUT `/api/v1/filters`
Updates or creates filter settings

**Query Parameters:**
- `user_id` (optional) - User ID for user-specific filters

**Request Body:**
```json
{
  "preferred": true,
  "auction_site": "namecheap",
  "tld": ".com",
  "has_statistics": true,
  "scored": true,
  "min_rank": 1,
  "max_rank": 1000,
  "min_score": 50.0,
  "max_score": 100.0,
  "sort_by": "score",
  "sort_order": "desc",
  "page_size": 100,
  "filter_name": "default",
  "is_default": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Filter settings saved successfully"
}
```

## Frontend Integration

The new `DomainsTablePage` component:
1. Loads filter settings from Supabase on mount
2. Applies filters when fetching auctions data
3. Provides "Set Filters" button to update filter settings
4. Provides "Load New Files" button to navigate to file upload

## Testing

After applying the migration:
1. Verify the table exists: `SELECT * FROM filters;`
2. Verify default filter exists: `SELECT * FROM filters WHERE is_default = true;`
3. Test API endpoints via `/docs` or Postman
4. Test frontend page loads filters correctly

## Rollback

If needed, rollback can be performed by:
```sql
DROP TABLE IF EXISTS filters CASCADE;
```










