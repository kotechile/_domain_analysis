# Data Inconsistency Analysis

## Problem

- **Summary shows**: 5,051,176 backlinks, 4,880 keywords (correct totals)
- **Details show**: Only 10 backlinks, 3 keywords (limited data)

## Root Cause Analysis

### Summary Data (Correct)
- Source: N8N Summary Workflow → DataForSEO Summary API
- Returns: **Totals only** (`total_backlinks`, `total_keywords`, `total_referring_domains`)
- Stored in: `report.data_for_seo_metrics.total_backlinks` and `total_keywords`
- Displayed in: Summary tile (`ReportSummary.tsx`)

### Detailed Data (Limited)
- Source: N8N Detailed Workflow → DataForSEO Detailed API
- Should return: **Individual items** (up to limit, e.g., 10,000)
- Stored in: `DetailedAnalysisData` with `json_data.items[]`
- Displayed in: BacklinksTable and KeywordsTable

## Possible Issues

### Issue 1: N8N Detailed Workflow Limit Too Low

**Check in N8N:**
1. Open "DataForSEO Backlinks Details" workflow
2. Check DataForSEO node configuration
3. Look for "Limit" field
4. Should be: `{{ $('Webhook').item.json.body.limit }}` or a high number (e.g., 10000)

**If limit is set to 10 or 100**, that explains why only 10 backlinks are returned.

### Issue 2: DataForSEO API Response Structure

The N8N workflow might be returning data in a different structure than expected.

**Expected structure:**
```json
{
  "items": [
    { "domain": "...", "anchor": "...", ... },
    ...
  ],
  "total_count": 10000
}
```

**Check N8N workflow:**
1. Look at the HTTP Request node (callback)
2. Check the JSON body structure
3. Verify it's sending `items` array correctly

### Issue 3: Webhook Handler Parsing

The webhook handler might be incorrectly parsing the N8N response.

**Check:** `backend/src/api/routes/n8n_webhook.py`
- Line 61-87: Normalization logic
- Line 89-91: Items array validation

## Verification Steps

### Step 1: Check N8N Workflow Execution

1. Go to N8N → Executions
2. Find the latest execution for "DataForSEO Backlinks Details"
3. Click on the DataForSEO node
4. Check the output:
   - How many items are in `tasks[0].result[0].items`?
   - What is the limit set in the node?

### Step 2: Check N8N HTTP Request Node (Callback)

1. In the same execution, click on the HTTP Request node
2. Check what data is being sent to the backend
3. Verify the structure:
   ```json
   {
     "request_id": "...",
     "domain": "...",
     "success": true,
     "data": {
       "items": [...],  // Should have many items
       "total_count": 10000
     }
   }
   ```

### Step 3: Check Backend Logs

Look for log messages:
```
N8N backlinks data received via webhook
items_count=10  // This shows how many items were received
```

If `items_count=10`, the N8N workflow is only sending 10 items.

### Step 4: Check Database

Query the database to see what's actually stored:

```sql
SELECT 
  json_data->>'items' as items,
  jsonb_array_length(json_data->'items') as item_count
FROM detailed_analysis_data
WHERE domain_name = 'wellroost.com'
  AND data_type = 'backlinks'
ORDER BY created_at DESC
LIMIT 1;
```

## Solutions

### Solution 1: Increase N8N Workflow Limit

In N8N "DataForSEO Backlinks Details" workflow:

1. Click on DataForSEO node
2. Find "Limit" field
3. Set to: `{{ $('Webhook').item.json.body.limit }}` (uses limit from webhook, default 10000)
4. Or set to: `10000` (fixed limit)
5. Save and test

### Solution 2: Fix HTTP Request Node Body Structure

In the HTTP Request node (callback), ensure the body is:

```json
{
  "request_id": "{{ $('Webhook').item.json.body.request_id }}",
  "domain": "{{ $('Webhook').item.json.body.domain }}",
  "success": true,
  "data": {
    "items": {{ $json.tasks[0].result[0].items }},
    "total_count": {{ $json.tasks[0].result[0].items | length }}
  },
  "error": null
}
```

**Important**: Make sure `items` is the full array, not limited.

### Solution 3: Check DataForSEO API Response

DataForSEO might be returning limited results due to:
- API tier/plan limits
- Rate limiting
- Request parameters

**Check in N8N:**
- DataForSEO node output
- Look for any warnings or limits in the response
- Check if `result_count` matches `items.length`

## Expected Behavior

### Summary Tile
- Shows **totals** from summary API: 5,051,176 backlinks, 4,880 keywords
- This is **correct** - these are the total counts

### Detailed Tables
- Should show **individual items** (up to the limit, e.g., 10,000)
- Currently showing only 10 backlinks and 3 keywords
- This is **incorrect** - should show many more items

## Summary

The **summary tile is correct** - it's showing totals from the summary API.

The **detailed tables are limited** - likely because:
1. N8N workflow has a low limit (e.g., 10)
2. DataForSEO API is returning limited results
3. HTTP Request node is not sending all items

**Action**: Check N8N workflow configuration, especially the limit in the DataForSEO node and the data structure in the HTTP Request callback node.


















