# Fix N8N Detailed Workflow - Empty Target Field

## Problem

The DataForSEO node in your "DataForSEO Backlinks Details" workflow is receiving an empty `target` field:

```json
{
  "status_code": 40501,
  "status_message": "Invalid Field: 'target'.",
  "target": "  "  // Empty spaces, not the domain!
}
```

## Root Cause

The DataForSEO node is not correctly extracting the domain from the webhook data. The expression is likely wrong or missing the `.body` part.

## Solution

### Step 1: Fix the Domain Field in DataForSEO Node

1. **Open** "DataForSEO Backlinks Details" workflow in N8N
2. **Click on the DataForSEO node**
3. **Find the "Target" or "Domain" field**
4. **Click the expression editor** (`fx` button) next to it
5. **Use this expression:**
   ```
   {{ $('Webhook').item.json.body.domain }}
   ```

**Important**: Make sure you include `.body` - the webhook data is nested under `body`!

### Step 2: Verify the Expression

To verify the expression is correct:

1. **Click "Execute Node"** on the Webhook node (or run the workflow in test mode)
2. **Click on the DataForSEO node**
3. **In the expression editor**, you should see available data
4. **Browse to**: `Webhook` → `item` → `json` → `body` → `domain`
5. **The value should show** the actual domain (e.g., "example.com")

### Step 3: Check Other Fields

While you're in the DataForSEO node, also verify:

- **Limit**: Should be `{{ $('Webhook').item.json.body.limit }}` or `10000`
- **Mode**: Should be `live` (since async is not supported in N8N community node)
- **Include Subdomains**: `true` (if desired)
- **Include Indirect Links**: `true` (if desired)

### Step 4: Test the Workflow

After fixing:

1. **Save the workflow** (Ctrl+S / Cmd+S)
2. **Make sure it's Active** (green toggle)
3. **Test with curl:**
   ```bash
   curl -X POST https://n8n.aichieve.net/webhook/webhook/backlinks-details \
     -H "Content-Type: application/json" \
     -d '{
       "domain": "test.com",
       "limit": 100,
       "callback_url": "https://httpbin.org/post",
       "request_id": "test-123",
       "type": "detailed"
     }'
   ```
4. **Check N8N Executions** - the DataForSEO node should now show:
   - `status_code: 20000` (success)
   - `target: "test.com"` (actual domain)
   - `result_count: > 0` (should have results)

## Common Mistakes

### ❌ Wrong Expression
```
{{ $json.domain }}           // Missing .body
{{ $('Webhook').json.domain }}  // Missing .item.json.body
{{ $json.body.domain }}      // Missing $('Webhook').item
```

### ✅ Correct Expression
```
{{ $('Webhook').item.json.body.domain }}
```

## Verification Checklist

After fixing, verify:

- [ ] DataForSEO node shows `status_code: 20000` (not 40501)
- [ ] `target` field shows the actual domain (not empty spaces)
- [ ] `result_count` is greater than 0
- [ ] `result` array contains backlink items
- [ ] HTTP Request node (callback) receives the full data

## Expected DataForSEO Response (After Fix)

```json
{
  "status_code": 20000,
  "status_message": "Ok.",
  "tasks": [{
    "status_code": 20000,
    "target": "example.com",  // Actual domain!
    "result_count": 100,      // Should be > 0
    "result": [{
      "items": [
        { "domain": "...", "anchor": "...", ... },
        // ... many items
      ]
    }]
  }]
}
```

## Why This Happens

N8N webhook nodes wrap the POST body in a `body` property. So:
- **Webhook receives**: `{ "domain": "example.com", ... }`
- **N8N stores it as**: `{ "body": { "domain": "example.com", ... } }`
- **To access it**: `$('Webhook').item.json.body.domain`

If you use `$json.domain` directly, you're looking at the wrong level and get empty/undefined values.

## Next Steps

1. Fix the domain expression in DataForSEO node
2. Test the workflow
3. Verify it returns actual backlink data
4. Check that the HTTP Request callback sends all items to backend


















