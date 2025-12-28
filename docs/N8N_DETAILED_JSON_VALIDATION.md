# N8N Detailed Backlinks JSON Structure Validation

## DataForSEO Response Structure

Based on the actual DataForSEO API response, the structure is:

```json
[
  {
    "version": "0.1.20251203",
    "status_code": 20000,
    "status_message": "Ok.",
    "tasks": [
      {
        "id": "12052044-1184-0269-0000-28a006586f0f",
        "status_code": 20000,
        "result": [
          {
            "target": "giniloh.com",
            "mode": "as_is",
            "total_count": 760,
            "items_count": 100,
            "items": [
              {
                "type": "backlink",
                "domain_from": "www.mysitefeed.com",
                "url_from": "https://www.mysitefeed.com/preview/557830.html",
                // ... all other backlink fields
              }
            ]
          }
        ]
      }
    ]
  }
]
```

## Backend Webhook Expected Format

The backend webhook endpoint (`/api/v1/n8n/webhook/backlinks`) expects:

```json
{
  "request_id": "uuid-string",
  "domain": "giniloh.com",
  "success": true,
  "data": {
    "items": [
      {
        "type": "backlink",
        "domain_from": "...",
        // ... all backlink fields
      }
    ],
    "total_count": 760,  // Optional but recommended
    "items_count": 100   // Optional but recommended
  },
  "error": null
}
```

## N8N HTTP Request Node Configuration

### ✅ CORRECT Configuration

**Body (JSON):**

```json
{
  "request_id": "{{ $('Webhook').item.json.body.request_id }}",
  "domain": "{{ $('Webhook').item.json.body.domain }}",
  "success": true,
  "data": {
    "items": {{ JSON.stringify($json.tasks[0].result[0].items || []) }},
    "total_count": {{ $json.tasks[0].result[0].total_count || 0 }},
    "items_count": {{ $json.tasks[0].result[0].items_count || 0 }}
  },
  "error": null
}
```

**OR (Alternative - Using Code Node to Build JSON):**

If the direct JSON approach fails, use a Code node before the HTTP Request node:

**Code Node (JavaScript):**
```javascript
// Extract data from DataForSEO response
const tasks = $input.item.json.tasks || [];
const result = tasks[0]?.result?.[0] || {};
const items = result.items || [];
const totalCount = result.total_count || 0;
const itemsCount = result.items_count || 0;

// Get original webhook data
const webhookData = $('Webhook').item.json.body;

// Build the response payload
return {
  json: {
    request_id: webhookData.request_id,
    domain: webhookData.domain,
    success: true,
    data: {
      items: items,
      total_count: totalCount,
      items_count: itemsCount
    },
    error: null
  }
};
```

Then in HTTP Request node, use:
- **Body Content Type**: JSON
- **Body**: `{{ $json }}` (entire output from Code node)

### ❌ INCORRECT Configurations (Common Mistakes)

**Mistake 1: Direct insertion without null check**
```json
{
  "items": {{ $json.tasks[0].result[0].items }}
}
```
**Problem**: If `items` is `null` or `undefined`, this creates invalid JSON: `"items": null` or `"items": undefined`

**Mistake 2: Missing array brackets**
```json
{
  "items": {{ $json.tasks[0].result[0].items }}
}
```
**Problem**: If items is not an array, this fails. Need to ensure it's always an array.

**Mistake 3: Wrong path**
```json
{
  "items": {{ $json.result[0].items }}
}
```
**Problem**: Missing `tasks[0]` level. DataForSEO wraps results in `tasks` array.

## Validation Checklist

Before running the workflow, verify:

- [ ] **DataForSEO Node Output**: Check that `$json.tasks[0].result[0].items` exists and is an array
- [ ] **Null Safety**: Use `|| []` fallback to ensure items is always an array
- [ ] **JSON Serialization**: Use `JSON.stringify()` if needed, or ensure N8N handles it automatically
- [ ] **Path Verification**: Confirm the exact path by clicking on DataForSEO node and checking OUTPUT panel

## Testing the Structure

### Step 1: Verify DataForSEO Node Output

1. Click on DataForSEO node in N8N
2. Check the OUTPUT panel
3. Verify the structure matches:
   ```
   tasks[0].result[0].items = [array of backlinks]
   ```

### Step 2: Test Expression in Code Node

Add a temporary Code node after DataForSEO node:

```javascript
const items = $input.item.json.tasks?.[0]?.result?.[0]?.items || [];
return {
  json: {
    items_count: items.length,
    first_item: items[0] || null,
    items_is_array: Array.isArray(items),
    total_count: $input.item.json.tasks?.[0]?.result?.[0]?.total_count || 0
  }
};
```

This will show you:
- If items is an array
- How many items there are
- The structure of the first item
- The total_count value

### Step 3: Validate JSON Before Sending

Add another Code node before HTTP Request to validate:

```javascript
const webhookData = $('Webhook').item.json.body;
const dataForSeoData = $input.item.json;
const result = dataForSeoData.tasks?.[0]?.result?.[0] || {};
const items = result.items || [];

const payload = {
  request_id: webhookData.request_id,
  domain: webhookData.domain,
  success: true,
  data: {
    items: items,
    total_count: result.total_count || 0,
    items_count: result.items_count || 0
  },
  error: null
};

// Validate JSON is valid
try {
  JSON.stringify(payload);
  return { json: payload };
} catch (e) {
  throw new Error(`Invalid JSON: ${e.message}`);
}
```

## Common Error: "JSON parameter needs to be valid JSON"

This error occurs when:
1. An expression evaluates to `null` or `undefined` within the JSON structure
2. An expression evaluates to a non-JSON-serializable value
3. The JSON structure itself is malformed

### Solution 1: Use JSON.stringify() with Fallback

```json
{
  "items": {{ JSON.stringify($json.tasks[0].result[0].items || []) }}
}
```

### Solution 2: Use Code Node (Recommended)

Build the entire JSON payload in a Code node, then pass it to HTTP Request node as `{{ $json }}`.

### Solution 3: Check for Null/Undefined

Before using in JSON, verify the path exists:

```javascript
// In Code node
const items = $input.item.json.tasks?.[0]?.result?.[0]?.items;
if (!items || !Array.isArray(items)) {
  throw new Error('Items array is missing or invalid');
}
```

## Final Recommended N8N Workflow Structure

```
Webhook → DataForSEO → IF (Error Check) → Code (Build JSON) → HTTP Request (Success/Error)
```

**Code Node (Success Path):**
```javascript
const webhookData = $('Webhook').item.json.body;
const dataForSeoData = $input.item.json;

// Validate response structure
if (!dataForSeoData.tasks || !dataForSeoData.tasks[0] || !dataForSeoData.tasks[0].result || !dataForSeoData.tasks[0].result[0]) {
  throw new Error('Invalid DataForSEO response structure');
}

const result = dataForSeoData.tasks[0].result[0];
const items = result.items || [];

return {
  json: {
    request_id: webhookData.request_id,
    domain: webhookData.domain,
    success: true,
    data: {
      items: items,
      total_count: result.total_count || 0,
      items_count: result.items_count || items.length
    },
    error: null
  }
};
```

**HTTP Request Node:**
- **Method**: POST
- **URL**: `{{ String($('Webhook').item.json.body.callback_url) }}`
- **Body Content Type**: JSON
- **Body**: `{{ $json }}`

This approach ensures:
- ✅ Always valid JSON
- ✅ Proper null/undefined handling
- ✅ Clear error messages if structure is wrong
- ✅ Type safety

















