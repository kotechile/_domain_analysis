# N8N "Invalid Host Header" Error Fix

## Error Message

```
"errorMessage": "Bad request - please check your parameters",
"errorDescription": "Invalid host header",
"httpCode": "400"
```

## Root Cause

This error occurs when N8N's HTTP Request node tries to call your backend via ngrok, but ngrok rejects the request because the `Host` header doesn't match what ngrok expects.

## Solution: Configure HTTP Request Node Headers

In your N8N HTTP Request node (the callback node that sends data back to your backend), you need to add a custom `Host` header.

### Step 1: Open HTTP Request Node

1. Go to your N8N workflow
2. Click on the **HTTP Request** node (the one that calls back to your backend)
3. This should be the node connected to the "False" path (success) of your IF node

### Step 2: Add Custom Headers

1. In the HTTP Request node, scroll down to **Options** section
2. Expand **Headers** section
3. Click **Add Header**
4. Add these headers:

**Header 1:**
- **Name**: `Host`
- **Value**: `{{ $('Webhook').item.json.body.callback_url.split('/')[2] }}`
  - This extracts the hostname from the callback URL (e.g., `overmild-untenuously-penney.ngrok-free.dev`)

**OR use a simpler approach - hardcode the Host header:**

- **Name**: `Host`
- **Value**: `overmild-untenuously-penney.ngrok-free.dev` (your actual ngrok hostname)

**Header 2 (if using ngrok-free.dev):**
- **Name**: `ngrok-skip-browser-warning`
- **Value**: `true`
  - This skips ngrok's browser warning page

### Step 3: Alternative - Use ngrok API to Get Hostname

If your ngrok URL changes frequently, you can extract it dynamically:

1. In the HTTP Request node, add a **Set** node before it
2. In the Set node, extract the hostname:
   - **Field**: `callback_host`
   - **Value**: `{{ $('Webhook').item.json.body.callback_url.split('/')[2] }}`
3. Then in HTTP Request node, use:
   - **Host header**: `{{ $json.callback_host }}`

### Step 4: Verify URL Format

Make sure your callback URL in the HTTP Request node is:
- **URL**: `{{ String($('Webhook').item.json.body.callback_url) }}`

## Complete HTTP Request Node Configuration

**Method**: POST

**URL**: `{{ String($('Webhook').item.json.body.callback_url) }}`

**Headers** (in Options → Headers):
- `Host`: `overmild-untenuously-penney.ngrok-free.dev` (your ngrok hostname)
- `ngrok-skip-browser-warning`: `true` (if using ngrok-free.dev)
- `Content-Type`: `application/json`

**Body** (JSON):
```json
{
  "request_id": "{{ $('Webhook').item.json.body.request_id }}",
  "domain": "{{ $('Webhook').item.json.body.domain }}",
  "success": true,
  "data": {
    "backlinks": {{ $json.tasks[0].result[0].backlinks }},
    "referring_domains": {{ $json.tasks[0].result[0].referring_domains }},
    "rank": {{ $json.tasks[0].result[0].rank }}
  },
  "error": null
}
```

## Alternative Solution: Use ngrok Static Domain

If you have a paid ngrok account, you can use a static domain which doesn't change:
1. Get a static domain from ngrok
2. Update `N8N_CALLBACK_URL` in backend `.env` to use the static domain
3. Update the Host header in N8N to match the static domain

## Alternative Solution: Disable Host Header Validation (Not Recommended)

If you control the backend, you could disable Host header validation, but this is **not recommended** for security reasons.

## Testing

After adding the Host header:

1. **Save the workflow**
2. **Activate the workflow**
3. **Test with curl:**
   ```bash
   curl -X POST https://n8n.aichieve.net/webhook/webhook/backlinks \
     -H "Content-Type: application/json" \
     -d '{
       "domain": "test.com",
       "callback_url": "https://overmild-untenuously-penney.ngrok-free.dev/api/v1/n8n/webhook/backlinks-summary",
       "request_id": "test-123",
       "type": "summary"
     }'
   ```
4. **Check N8N Executions** - the HTTP Request node should now succeed

## Why This Happens

- ngrok validates the `Host` header to prevent Host header attacks
- N8N's HTTP Request node may not send the correct Host header by default
- The Host header must match the domain in the URL you're calling

## Notes

- This fix applies to **both** summary and detailed backlinks workflows
- Make sure to update the Host header in **both** HTTP Request nodes (success and error callbacks)
- If your ngrok URL changes, update the Host header value accordingly

















