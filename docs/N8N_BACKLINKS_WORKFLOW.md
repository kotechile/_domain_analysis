# N8N DataForSEO Backlinks Single Page Workflow

This guide provides a complete, improved workflow for fetching backlinks data using N8N's DataForSEO nodes. This workflow is designed for subscriptions that don't allow direct HTTP API access.

## Overview

The workflow receives a webhook trigger from your backend, calls DataForSEO's Backlinks API using N8N's DataForSEO node, and sends the results back to your backend via callback.

## Workflow Structure

```
Webhook Trigger → DataForSEO Backlinks Node → IF (Error Check) → HTTP Request (Callback)
```

## Step-by-Step Setup

### 1. Create New Workflow

1. Log into your N8N instance
2. Click **"New Workflow"**
3. Name it: **"DataForSEO Backlinks Single Page"**

### 2. Add Webhook Trigger Node

1. Add a **Webhook** node as the first node
2. Configure:
   - **HTTP Method**: `POST`
   - **Path**: `/webhook/backlinks-details` (or your preferred path)
   - **Response Mode**: "Respond When Last Node Finishes"
   - **Response Data**: "First Entry JSON"
3. Click **"Execute Node"** to activate the webhook
4. Copy the webhook URL (e.g., `https://n8n.aichieve.net/webhook/webhook/backlinks-details`)
5. Update `N8N_WEBHOOK_URL` in your backend `.env` file

**Expected Webhook Payload:**
```json
{
  "domain": "example.com",
  "limit": 10000,
  "callback_url": "https://your-backend.com/api/v1/n8n/webhook/backlinks",
  "request_id": "uuid-here",
  "type": "detailed"
}
```

### 3. Add DataForSEO Node

1. Add a **DataForSEO** node after the webhook
2. **Install DataForSEO Node** (if not already installed):
   - Go to N8N Community Nodes
   - Search for "DataForSEO"
   - Install the community node

3. **Configure Authentication:**
   - Click **"Create New Credential"** or select existing
   - **Login**: Your DataForSEO login
   - **Password**: Your DataForSEO password
   - Save credentials

4. **Configure Node Settings:**
   - **Operation**: `Get Backlinks`
   - **Resource**: `Backlinks` (auto-selected)
   - **Target (Domain)**: `{{ $('Webhook').item.json.body.domain }}`
     - **IMPORTANT**: Use the expression editor (`fx` button) and ensure you include `.body`
   - **Mode**: `As Is` (Live/synchronous mode - required for N8N community node)
   - **Limit**: `{{ $('Webhook').item.json.body.limit }}` or `10000`
   - **Include Subdomains**: `true` (toggle ON)
   - **Include Indirect Links**: `true` (toggle ON)
   - **Exclude Internal Links**: `true` (toggle ON - recommended)
   - **Backlink Status**: `Live` (recommended)
   - **Rank Scale**: `0 - 100 Scale` (or your preference)
   - **Filters**: Leave empty or use: `["dofollow", "=", true]`

**Critical Configuration Notes:**
- **Mode "As Is"** = Live/synchronous mode (returns immediately, no async polling needed)
- **Target Field**: Must use `{{ $('Webhook').item.json.body.domain }}` - the `.body` part is essential!
- **Limit**: Start with 100-2000 for testing, increase to 10000 for production
- The DataForSEO community node does NOT support async mode, so "As Is" is required

### 4. Add IF Node (Error Detection)

1. Add an **IF** node after the DataForSEO node
2. Configure:
   - **Condition 1**:
     - **Value 1**: `{{ $json.status_code }}`
     - **Operation**: "Not Equal"
     - **Value 2**: `20000`
   - **True Path** (Error): Connect to Error Callback HTTP Request
   - **False Path** (Success): Connect to Success Callback HTTP Request

**DataForSEO Response Structure:**
```json
{
  "status_code": 20000,  // 20000 = success, other codes = error
  "status_message": "Ok.",
  "tasks": [
    {
      "id": "task-id",
      "result": [
        {
          "items": [...],  // Array of backlink items
          "total_count": 1234
        }
      ]
    }
  ]
}
```

### 5. Add HTTP Request Node (Success Callback)

1. Add an **HTTP Request** node for success cases
2. Connect from the **False** path of the IF node
3. Configure:
   - **Method**: `POST`
   - **URL**: `{{ $('Webhook').item.json.body.callback_url }}`
   - **Authentication**: None (or add if your backend requires it)
   - **Body Content Type**: `JSON`
   - **Body** (use expression editor):
```json
{
  "request_id": "{{ $('Webhook').item.json.body.request_id }}",
  "domain": "{{ $('Webhook').item.json.body.domain }}",
  "success": true,
  "data": {
    "items": {{ $json.tasks[0].result[0].items }},
    "total_count": {{ $json.tasks[0].result[0].total_count || $json.tasks[0].result[0].items.length || 0 }}
  },
  "error": null
}
```

**Alternative Body (if items structure differs):**
```json
{
  "request_id": "{{ $('Webhook').item.json.body.request_id }}",
  "domain": "{{ $('Webhook').item.json.body.domain }}",
  "success": true,
  "data": {{ $json.tasks[0].result[0] }},
  "error": null
}
```

### 6. Add HTTP Request Node (Error Callback)

1. Add another **HTTP Request** node for error cases
2. Connect from the **True** path of the IF node
3. Configure:
   - **Method**: `POST`
   - **URL**: `{{ $('Webhook').item.json.body.callback_url }}`
   - **Body Content Type**: `JSON`
   - **Body**:
```json
{
  "request_id": "{{ $('Webhook').item.json.body.request_id }}",
  "domain": "{{ $('Webhook').item.json.body.domain }}",
  "success": false,
  "data": null,
  "error": "{{ $json.status_message || 'Unknown error' }} (Code: {{ $json.status_code }})"
}
```

## Complete Workflow JSON (Import Ready)

Here's a complete workflow JSON you can import into N8N:

```json
{
  "name": "DataForSEO Backlinks Single Page",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "backlinks-details",
        "responseMode": "responseNode",
        "options": {}
      },
      "id": "webhook-trigger",
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1,
      "position": [250, 300],
      "webhookId": "your-webhook-id-here"
    },
    {
      "parameters": {
        "operation": "getBacklinks",
        "domain": "={{ $('Webhook').item.json.body.domain }}",
        "limit": "={{ $('Webhook').item.json.body.limit }}",
        "mode": "as_is",
        "includeSubdomains": true,
        "includeIndirectLinks": true,
        "excludeInternalLinks": true,
        "backlinkStatus": "live",
        "rankScale": "0-100"
      },
      "id": "dataforseo-backlinks",
      "name": "DataForSEO Backlinks",
      "type": "n8n-nodes-community.dataForSeo",
      "typeVersion": 1,
      "position": [450, 300],
      "credentials": {
        "dataForSeoApi": {
          "id": "your-credentials-id",
          "name": "DataForSEO Account"
        }
      }
    },
    {
      "parameters": {
        "conditions": {
          "options": {
            "caseSensitive": true,
            "leftValue": "",
            "typeValidation": "strict"
          },
          "conditions": [
            {
              "id": "error-check",
              "leftValue": "={{ $json.status_code }}",
              "rightValue": 20000,
              "operator": {
                "type": "number",
                "operation": "notEqual"
              }
            }
          ],
          "combinator": "and"
        },
        "options": {}
      },
      "id": "if-error",
      "name": "IF Error Check",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [650, 300]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "={{ $('Webhook').item.json.body.callback_url }}",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "request_id",
              "value": "={{ $('Webhook').item.json.body.request_id }}"
            },
            {
              "name": "domain",
              "value": "={{ $('Webhook').item.json.body.domain }}"
            },
            {
              "name": "success",
              "value": "=true"
            },
            {
              "name": "data",
              "value": "={{ $json.tasks[0].result[0] }}"
            },
            {
              "name": "error",
              "value": "=null"
            }
          ]
        },
        "options": {}
      },
      "id": "http-success",
      "name": "HTTP Request (Success)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.1,
      "position": [850, 200]
    },
    {
      "parameters": {
        "method": "POST",
        "url": "={{ $('Webhook').item.json.body.callback_url }}",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "request_id",
              "value": "={{ $('Webhook').item.json.body.request_id }}"
            },
            {
              "name": "domain",
              "value": "={{ $('Webhook').item.json.body.domain }}"
            },
            {
              "name": "success",
              "value": "=false"
            },
            {
              "name": "data",
              "value": "=null"
            },
            {
              "name": "error",
              "value": "={{ $json.status_message || 'Unknown error' }} (Code: {{ $json.status_code }})"
            }
          ]
        },
        "options": {}
      },
      "id": "http-error",
      "name": "HTTP Request (Error)",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.1,
      "position": [850, 400]
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{"node": "DataForSEO Backlinks", "type": "main", "index": 0}]]
    },
    "DataForSEO Backlinks": {
      "main": [[{"node": "IF Error Check", "type": "main", "index": 0}]]
    },
    "IF Error Check": {
      "main": [
        [{"node": "HTTP Request (Success)", "type": "main", "index": 0}],
        [{"node": "HTTP Request (Error)", "type": "main", "index": 0}]
      ]
    }
  },
  "pinData": {},
  "settings": {
    "executionOrder": "v1"
  },
  "staticData": null,
  "tags": [],
  "triggerCount": 0,
  "updatedAt": "2024-01-01T00:00:00.000Z",
  "versionId": "1"
}
```

**To Import:**
1. Copy the JSON above
2. In N8N, click **"Import from File"** or **"Import from URL"**
3. Paste the JSON
4. Update:
   - Webhook ID (get from executing the webhook node)
   - DataForSEO credentials ID
   - Adjust positions if needed

## Testing the Workflow

### 1. Test with N8N's Test Mode

1. Click **"Execute Workflow"** button
2. In the Webhook node, you'll see test data
3. Manually set test data:
```json
{
  "domain": "example.com",
  "limit": 100,
  "callback_url": "https://webhook.site/your-unique-url",
  "request_id": "test-123",
  "type": "detailed"
}
```
4. Execute the workflow
5. Check the HTTP Request node output

### 2. Test with Backend

1. Make sure workflow is **Active** (green toggle)
2. Ensure `N8N_WEBHOOK_URL` is set in backend `.env`
3. Trigger analysis from your frontend
4. Check N8N execution logs
5. Verify data received in backend webhook endpoint

## Troubleshooting

### Issue: Empty Target Field

**Error**: `"target": "  "` (empty spaces)

**Solution**: 
- Check the DataForSEO node's Target field
- Must use: `{{ $('Webhook').item.json.body.domain }}`
- The `.body` part is essential!

### Issue: Workflow Times Out

**Error**: Backend waits 120 seconds but no data received

**Solutions**:
1. Check N8N execution logs for errors
2. Verify callback URL is accessible from N8N
3. Check DataForSEO credentials are valid
4. Reduce limit (try 100-1000 first)
5. Check backend webhook endpoint is working

### Issue: DataForSEO Returns Error

**Error**: `status_code: 40501` or other error codes

**Solutions**:
1. Verify DataForSEO credentials
2. Check domain format (no http://, no www.)
3. Verify limit is within your plan limits
4. Check DataForSEO account balance/limits

### Issue: Callback Not Received

**Error**: Backend doesn't receive webhook callback

**Solutions**:
1. Verify callback URL is correct in backend `.env`
2. Check if backend is accessible from N8N (use ngrok for local dev)
3. Check backend webhook endpoint logs
4. Verify HTTP Request node in N8N is using correct URL

## Best Practices

1. **Start Small**: Test with limit=100 first, then increase
2. **Monitor Costs**: DataForSEO charges per API call - monitor usage
3. **Error Handling**: Always include error callbacks
4. **Logging**: Enable N8N execution logs for debugging
5. **Rate Limiting**: Be aware of DataForSEO rate limits
6. **Caching**: Backend caches results - don't re-fetch unnecessarily

## Backend Configuration

Ensure your backend `.env` has:

```bash
# N8N Integration Settings
N8N_ENABLED=true
N8N_WEBHOOK_URL=https://n8n.aichieve.net/webhook/webhook/backlinks-details
N8N_CALLBACK_URL=https://your-backend.com/api/v1/n8n/webhook/backlinks
N8N_TIMEOUT=120
N8N_USE_FOR_BACKLINKS=true
```

## Next Steps

- For bulk operations (multiple domains), see `N8N_BULK_WORKFLOWS.md`
- For summary backlinks (totals only), see `N8N_SETUP.md` (Summary section)
- For async operations, you'll need to implement custom HTTP Request nodes (not covered here)











