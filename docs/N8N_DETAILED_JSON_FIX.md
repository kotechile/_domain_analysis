# N8N Detailed Backlinks JSON Fix

## Error Message

```
"errorMessage": "JSON parameter needs to be valid JSON"
```

This error occurs when the HTTP Request node's JSON body contains invalid JSON syntax, usually because an expression returns `undefined` or is not properly formatted.

## Root Cause

The `items` array expression in the HTTP Request body might be:
1. Returning `undefined` (if DataForSEO response structure is different)
2. Not properly stringified (needs to be valid JSON)
3. Missing or in wrong location in DataForSEO response

## Solution: Fix HTTP Request Node Body

### Step 1: Check DataForSEO Node Output

First, verify what the DataForSEO node actually returns:

1. Go to N8N → Executions
2. Find the latest detailed backlinks execution
3. Click on the **DataForSEO** node
4. Check the **OUTPUT** panel
5. Look for the structure - it should be:
   ```
   tasks[0].result[0].items[]
   ```

### Step 2: Fix HTTP Request Node Body

In your **HTTP Request node** (success callback for detailed backlinks), use this body configuration:

**Option 1: Using JSON.stringify() (Recommended)**

Set **Body Content Type** to: `JSON`

**Body** (use the expression editor `</>` icon):
```json
{
  "request_id": "{{ $('Webhook').item.json.body.request_id }}",
  "domain": "{{ $('Webhook').item.json.body.domain }}",
  "success": true,
  "data": {
    "items": {{ JSON.stringify($json.tasks[0].result[0].items || []) }},
    "total_count": {{ $json.tasks[0].result[0].items?.length || $json.tasks[0].result_count || 0 }}
  },
  "error": null
}
```

**Option 2: Using Conditional Check (Safer)**

If `items` might be undefined, use this:

```json
{
  "request_id": "{{ $('Webhook').item.json.body.request_id }}",
  "domain": "{{ $('Webhook').item.json.body.domain }}",
  "success": true,
  "data": {{ JSON.stringify({
    "items": $json.tasks[0].result[0].items || [],
    "total_count": $json.tasks[0].result[0].items?.length || $json.tasks[0].result_count || 0
  }) }},
  "error": null
}
```

**Option 3: Manual JSON Construction (Most Reliable)**

Use a **Code** node or **Set** node before the HTTP Request to prepare the data:

1. Add a **Set** node before HTTP Request
2. Configure it to set:
   - **Field**: `items_array`
   - **Value**: `{{ $json.tasks[0].result[0].items || [] }}`
   - **Field**: `total_count`
   - **Value**: `{{ $json.tasks[0].result[0].items?.length || $json.tasks[0].result_count || 0 }}`

3. Then in HTTP Request node, use:
```json
{
  "request_id": "{{ $('Webhook').item.json.body.request_id }}",
  "domain": "{{ $('Webhook').item.json.body.domain }}",
  "success": true,
  "data": {
    "items": {{ JSON.stringify($json.items_array) }},
    "total_count": {{ $json.total_count }}
  },
  "error": null
}
```

### Step 3: Verify DataForSEO Response Structure

The DataForSEO detailed backlinks response structure should be:

```json
{
  "status_code": 20000,
  "tasks": [{
    "status_code": 20000,
    "result": [{
      "items": [
        { "domain_from": "...", "url_from": "...", "anchor": "...", ... },
        ...
      ],
      "total_count": 100
    }]
  }]
}
```

**Important**: The `items` array is at `tasks[0].result[0].items`, not `tasks[0].result.items`.

### Step 4: Common Issues and Fixes

**Issue 1: `items` is undefined**
- **Fix**: Use `|| []` fallback: `{{ $json.tasks[0].result[0].items || [] }}`

**Issue 2: `items` is not an array**
- **Fix**: Check DataForSEO node output - might need to access different path
- **Check**: `tasks[0].result[0]` might be the items array directly

**Issue 3: Expression returns object instead of JSON string**
- **Fix**: Use `JSON.stringify()`: `{{ JSON.stringify($json.tasks[0].result[0].items) }}`

**Issue 4: Nested structure different**
- **Fix**: Check actual DataForSEO output and adjust path accordingly
- **Common paths**:
  - `$json.tasks[0].result[0].items` (most common)
  - `$json.tasks[0].result.items` (if result is not an array)
  - `$json.tasks[0].items` (if structure is flat)

### Step 5: Test the Fix

1. **Save the workflow**
2. **Activate the workflow**
3. **Test with curl:**
   ```bash
   curl -X POST https://n8n.aichieve.net/webhook/webhook/backlinks-details \
     -H "Content-Type: application/json" \
     -d '{
       "domain": "test.com",
       "limit": 100,
       "callback_url": "https://overmild-untenuously-penney.ngrok-free.dev/api/v1/n8n/webhook/backlinks",
       "request_id": "test-123",
       "type": "detailed"
     }'
   ```
4. **Check N8N Executions**:
   - DataForSEO node should show `status_code: 20000`
   - HTTP Request node should succeed (no JSON error)
   - Check the OUTPUT of HTTP Request to see what was sent

## Recommended Configuration

**HTTP Request Node (Detailed Backlinks - Success Callback):**

- **Method**: POST
- **URL**: `{{ String($('Webhook').item.json.body.callback_url) }}`
- **Body Content Type**: JSON
- **Body**:
```json
{
  "request_id": "{{ $('Webhook').item.json.body.request_id }}",
  "domain": "{{ $('Webhook').item.json.body.domain }}",
  "success": true,
  "data": {
    "items": {{ JSON.stringify($json.tasks[0].result[0].items || []) }},
    "total_count": {{ $json.tasks[0].result[0].items?.length || $json.tasks[0].result_count || 0 }}
  },
  "error": null
}
```

**Headers** (in Options → Headers):
- `ngrok-skip-browser-warning`: `true` (if using ngrok-free.dev)

## Verification

After fixing, verify:
- [ ] HTTP Request node executes without JSON error
- [ ] Backend receives the webhook successfully
- [ ] Backend logs show "N8N backlinks data saved successfully"
- [ ] Items count matches expected number

## Debugging Tips

1. **Use Set Node to Inspect**: Add a Set node before HTTP Request to see what `$json.tasks[0].result[0]` actually contains
2. **Check DataForSEO Output**: Always verify the actual structure in N8N Executions
3. **Test with Small Limit**: Start with limit=10 to test, then increase
4. **Use JSON.stringify()**: Always stringify arrays/objects when embedding in JSON body


























