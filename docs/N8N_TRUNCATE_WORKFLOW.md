# N8N Truncate Auctions Workflow

This document describes how to set up an N8N workflow to truncate the auctions table using SQL.

## Overview

Instead of deleting records via REST API (which is slow and can hit URI length limits), the backend can trigger an N8N workflow that executes SQL directly on the database. This is much faster for large tables.

## Workflow Setup

### 1. Create Webhook Trigger

- Add a **Webhook** node
- Set method to **POST**
- Set path to `/webhook/truncate-auctions` (or your preferred path)
- Save the workflow to get the webhook URL

### 2. Add SQL Execute Node

- Add a **Postgres** or **Supabase** node (depending on your setup)
- Configure database connection to your Supabase instance
- Set operation to **Execute Query**
- Add the SQL query:

```sql
TRUNCATE TABLE auctions RESTART IDENTITY CASCADE;
```

**Note:** `RESTART IDENTITY` resets auto-increment sequences, and `CASCADE` handles foreign key constraints if any.

### 3. Add Response Node

- Add a **Respond to Webhook** node
- Set response code to **200**
- Set response body (optional):

```json
{
  "success": true,
  "message": "Auctions table truncated successfully",
  "request_id": "{{ $json.request_id }}"
}
```

### 4. Error Handling

- Add error handling to catch SQL errors
- Return appropriate error response if truncation fails

## Configuration

Add the webhook URL to your `.env` file:

```env
N8N_ENABLED=true
N8N_WEBHOOK_URL_TRUNCATE=https://your-n8n-instance.com/webhook/truncate-auctions
```

Or the backend will try to construct it from `N8N_WEBHOOK_URL` by appending `/truncate-auctions`.

## How It Works

1. When uploading a CSV with >100k existing records, the backend triggers the N8N webhook
2. N8N executes `TRUNCATE TABLE auctions` directly on the database
3. This is much faster than REST API deletions (seconds vs hours)
4. The backend waits briefly and verifies the truncation completed

## Benefits

- **Fast**: SQL TRUNCATE is instant even for millions of records
- **No URI limits**: Direct SQL execution avoids REST API limitations
- **Reliable**: Database-level operation is more reliable than API calls
- **Scalable**: Works efficiently regardless of table size

## Alternative: Direct RPC Function

If you prefer not to use N8N, you can create a database function and use RPC:

```sql
CREATE OR REPLACE FUNCTION truncate_auctions_table()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    TRUNCATE TABLE auctions RESTART IDENTITY CASCADE;
END;
$$;
```

The backend will try RPC first, then N8N, then fall back to other methods.


















