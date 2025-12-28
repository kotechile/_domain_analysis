# N8N DataForSEO Backlinks Integration Setup Guide

This guide explains how to set up N8N to fetch backlink data from DataForSEO and integrate it with the Domain Analysis System.

## Overview

The integration allows you to use N8N's DataForSEO node to fetch backlink data, avoiding direct API consumption limits. The workflow is:

1. Backend triggers N8N webhook with domain information
2. N8N workflow uses DataForSEO node to fetch backlinks
3. N8N sends results back to backend webhook endpoint
4. Backend saves data to database

## Prerequisites

- N8N instance running and accessible
- DataForSEO account with API credentials
- Backend application running and accessible from N8N

## N8N Configuration in Coolify

If you're running N8N via Coolify and encounter the secure cookie warning, you have a few options:

### Option 1: Configure HTTPS (Recommended)

Set up proper TLS/HTTPS for your N8N instance in Coolify. This is the most secure option.

#### Steps to Configure HTTPS in Coolify:

1. **Access Your N8N Service in Coolify**
   - Navigate to your Coolify dashboard
   - Find and click on your N8N service

2. **Configure Domain/Subdomain**
   - In the service settings, look for the "Domains" or "FQDN" section
   - Ensure your N8N service has a domain configured (e.g., `n8n.yourdomain.com`)
   - If using the sslip.io domain provided by Coolify, that should work too

3. **Enable SSL/TLS**
   - In Coolify, SSL/TLS is typically handled automatically via Let's Encrypt
   - Look for "SSL" or "TLS" settings in your service configuration
   - If there's an "Enable SSL" toggle, turn it on
   - Coolify should automatically:
     - Request a Let's Encrypt certificate
     - Configure the reverse proxy (Traefik) to handle HTTPS
     - Set up automatic certificate renewal

4. **Verify HTTPS is Working**
   - After enabling SSL, wait a few minutes for certificate provisioning
   - Access your N8N instance via HTTPS: `https://n8n.aichieve.net`
   - You should see a padlock icon in your browser
   - The secure cookie warning should disappear

5. **Update Environment Variables**
   - Once HTTPS is working, ensure `N8N_SECURE_COOKIE` is set to `true` (or remove it to use default)
   - Update your backend `N8N_WEBHOOK_URL` to use `https://` instead of `http://`
   - Update your backend `N8N_CALLBACK_URL` to use `https://` if your backend also has HTTPS

#### Troubleshooting HTTPS in Coolify:

- **Certificate Not Issued**: Check Coolify logs for Let's Encrypt errors. Common issues:
  - Domain not properly configured
  - DNS not pointing to Coolify server
  - Rate limits from Let's Encrypt (wait 1 hour if you've made many requests)

- **Mixed Content Warnings**: Ensure all URLs use `https://` consistently

- **Certificate Expired**: Coolify should auto-renew, but check renewal logs if issues occur

- **Port Configuration**: Ensure ports 80 and 443 are open and properly configured in Coolify

### Option 2: Disable Secure Cookie (For Development/Testing)

If you're running in a development environment or behind a reverse proxy that handles SSL termination, you can disable the secure cookie requirement by adding this environment variable to your N8N service in Coolify:

```
N8N_SECURE_COOKIE=false
```

**Note**: Only use this option if you understand the security implications. In production with proper HTTPS, you should not need this.

### Option 3: Use Localhost (For Local Development Only)

If you're accessing N8N locally for development, use `localhost` instead of the IP address or domain name.

### Setting Environment Variables in Coolify

1. Go to your N8N service in Coolify
2. Navigate to the "Environment Variables" section
3. Add the variable:
   - **Key**: `N8N_SECURE_COOKIE`
   - **Value**: `false` (if using Option 2)
4. Save and restart the service

## Step 1: Configure Backend Environment Variables

Add the following environment variables to your backend `.env` file:

```bash
# N8N Integration Settings
N8N_ENABLED=true
N8N_WEBHOOK_URL=https://n8n.aichieve.net/webhook/webhook/backlinks-details
N8N_CALLBACK_URL=https://your-backend-url/api/v1/n8n/webhook/backlinks
N8N_TIMEOUT=60
N8N_USE_FOR_BACKLINKS=true
```

**Important Notes:**
- **For Local Development**: Use ngrok or similar to expose your local backend:
  ```bash
  # Install ngrok: brew install ngrok
  # Start tunnel: ngrok http 8000
  # Use the ngrok HTTPS URL for N8N_CALLBACK_URL
  N8N_CALLBACK_URL=https://abc123.ngrok.io/api/v1/n8n/webhook/backlinks
  ```
- **For Production**: Deploy backend to same server or use a public URL:
  ```bash
  N8N_CALLBACK_URL=https://api.aichieve.net/api/v1/n8n/webhook/backlinks
  ```
- The `N8N_WEBHOOK_URL` should point to your N8N webhook endpoint
- **Critical**: The callback URL MUST be accessible from N8N (on Hostinger)
- **DNS Configuration**: The DNS record for `n8n.aichieve.net` has been configured to point to `72.61.72.70`
- **HTTPS**: Once SSL is configured in Coolify, use `https://` URLs

**See `N8N_BACKEND_INTEGRATION.md` for detailed integration guide including local development setup.**

## Step 2: Create N8N Workflow

### Important: Summary vs Detailed Backlinks

**Understanding Your Backend's Requirements:**

Your backend needs **both** summary and detailed backlinks:

1. **Summary API** (Essential Data Phase):
   - Called first to get totals: `total_backlinks`, `total_referring_domains`, `rank`
   - Used in `_collect_essential_data()` method
   - Currently: Backend calls DataForSEO directly for this
   - **Note**: Summary is NOT currently integrated with N8N webhook (backend calls API directly)
   - **Future**: Could be moved to N8N if desired

2. **Detailed Backlinks** (Detailed Data Phase):
   - **Detailed Live**: Fallback when async fails or for small requests (limit: 100-1000)
   - **Detailed Async**: Preferred for comprehensive analysis (limit: up to 10,000)
   - Currently: Backend uses `DataForSEOAsyncService` with POST → poll → GET pattern
   - **N8N Integration**: This is what your N8N workflow should handle

**Current N8N Implementation Status:**

✅ **Summary Workflow** (CURRENT - For Testing):
- **Operation**: "Get Backlinks Summary"
- **Resource**: "Backlinks Summary" or "Summary"
- **Returns**: Summary metrics object
- **Structure**: `tasks[0].result[0]` contains the summary object
- **Note**: Currently used for testing, but backend doesn't use N8N for summary yet

⚠️ **Detailed Backlinks Workflow** (TO IMPLEMENT):
- **Option A - Live Endpoint** (Simpler, for 100-1000 limit):
  - **Operation**: "Get Backlinks"
  - **Resource**: "Backlinks"
  - **Mode**: "live" (synchronous, returns immediately)
  - **Limit**: 100-1000 (smaller requests)
  - **Use Case**: Fallback or quick detailed data

- **Option B - Async Pattern** (Preferred, for up to 10,000):
  - **Operation**: "Get Backlinks" 
  - **Resource**: "Backlinks"
  - **Mode**: "as_is" (asynchronous, requires polling)
  - **Limit**: Up to 10,000
  - **Use Case**: Comprehensive analysis
  - **Note**: N8N DataForSEO node may handle async automatically, or you may need to implement polling

**Output Structure Verification:**
- ✅ **Summary**: `$json.tasks[0].result[0].backlinks` (verified working)
- ✅ **Summary**: `$json.tasks[0].result[0].referring_domains` (verified working)
- ✅ **Summary**: `$json.tasks[0].result[0].rank` (verified working)
- ⚠️ **Detailed**: `$json.tasks[0].result[0].items[]` (to be implemented)

**Important**: The backend webhook endpoint (`/api/v1/n8n/webhook/backlinks`) currently only handles **detailed backlinks** data (expects `items` array). Summary data would need a separate endpoint or modification.

### 2.1 Create New Workflow

1. Log into your N8N instance
2. Click "New Workflow" to create a new workflow
3. Name it "DataForSEO Backlinks Fetcher" or similar

### 2.2 Add Webhook Trigger Node

1. Add a **Webhook** node as the trigger
2. Configure the webhook:
   - **HTTP Method**: POST
   - **Path**: `/webhook/backlinks` (or your preferred path)
   - **Response Mode**: "Respond When Last Node Finishes"
   - **Response Data**: "First Entry JSON"
3. Click "Execute Node" to get the webhook URL
4. Copy the webhook URL and update `N8N_WEBHOOK_URL` in your backend `.env`

### 2.3 Add DataForSEO Backlinks Node

1. Add a **DataForSEO** node after the webhook
2. Configure the node:
   - **Operation**: "Get Backlinks Summary" (for testing) or "Get Backlinks" (for detailed data)
   - **Resource**: "Backlinks" or "Backlinks Summary"
   - **Domain**: **IMPORTANT** - Use this expression:
     - `{{ $('Webhook').item.json.body.domain }}` (**CORRECT - Webhook data is in body property**)
   - **Limit**: Use `{{ $('Webhook').item.json.body.limit }}` or set a default value (e.g., 10000)
   - **Filters**: Configure as needed (e.g., dofollow links only)
3. **Authentication**: 
   - Add your DataForSEO credentials:
     - **Login**: Your DataForSEO login
     - **Password**: Your DataForSEO password
   - Or use N8N credentials management

**Important Note on Webhook Data Structure:**
- N8N Webhook nodes wrap the POST body in a `body` property
- The actual payload is at: `$('Webhook').item.json.body`
- So to access `domain`, use: `{{ $('Webhook').item.json.body.domain }}`
- To access `callback_url`, use: `{{ $('Webhook').item.json.body.callback_url }}`

**Troubleshooting Domain Field:**
- If you see `"target": "`` "` (empty backticks), the domain expression is not resolving
- **Solution**: Use `{{ $('Webhook').item.json.body.domain }}` (note the `.body` part)
- Click the expression editor icon (`</>`) next to the Domain field to browse available data
- Make sure the Webhook node is connected to the DataForSEO node

### 2.4 Add HTTP Request Node (Callback)

1. Add an **HTTP Request** node after the DataForSEO node (or after IF node for success path)
2. Configure the node:
   - **Method**: POST
   - **URL**: **IMPORTANT** - Use this expression:
     - `{{ String($('Webhook').item.json.body.callback_url) }}` (**RECOMMENDED - String() ensures proper type conversion**)
     - OR: `{{ $('Webhook').item.json.body.callback_url }}` (if String() causes issues)
     - **Note**: If you see "Invalid URL" error, use `String()` wrapper
   - **Authentication**: None (or add if your backend requires it)
   - **Body Content Type**: JSON
   - **Body**: 
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
   
   **Verified Output Structure:**
   - DataForSEO Summary returns: `tasks[0].result[0]` (array with one result object)
   - Summary fields: `backlinks`, `referring_domains`, `rank`
   - The expressions above are correct for summary data
   **Note:** 
   - For summary data, use the structure above
   - For detailed backlinks, use `"items": {{ $json.tasks[0].result[0].items }}`
   - Adjust paths based on your actual DataForSEO node output structure
   - **Always use `.body.` when referencing Webhook node data**: `$('Webhook').item.json.body.field_name`

### 2.5 Add Error Handling

1. Add an **IF** node after DataForSEO node to check for errors
2. Configure the IF node with one of these conditions:

   **Option 1 - Check DataForSEO Status Code (RECOMMENDED):**
   - **Condition 1**: 
     - **Value 1**: `{{ $json.status_code }}`
     - **Operation**: "Not Equal"
     - **Value 2**: `20000` (20000 = success in DataForSEO)
   - **True Path**: Connect to HTTP Request node (Error Callback)
   - **False Path**: Connect to HTTP Request node (Success Callback)
   
   **Option 2 - Check Tasks Error Count:**
   - **Condition 1**: 
     - **Value 1**: `{{ $json.tasks_error }}`
     - **Operation**: "Larger"
     - **Value 2**: `0`
   - **True Path**: Connect to HTTP Request node (Error Callback)
   - **False Path**: Connect to HTTP Request node (Success Callback)
   
   **Option 3 - Check Task Status Code:**
   - **Condition 1**: 
     - **Value 1**: `{{ $json.tasks[0].status_code }}`
     - **Operation**: "Not Equal"
     - **Value 2**: `20000`
   - **True Path**: Connect to HTTP Request node (Error Callback)
   - **False Path**: Connect to HTTP Request node (Success Callback)
   
   **Option 4 - Check if Error Message Exists (More Specific):**
   - **Condition 1**: 
     - **Value 1**: `{{ $json.__error?.message }}`
     - **Operation**: "Exists"
   - **True Path**: Connect to HTTP Request node (Error Callback)
   - **False Path**: Connect to HTTP Request node (Success Callback)

**Recommended:** Use **Option 1** (check status_code) as it's the most reliable way to detect DataForSEO API errors.

3. **HTTP Request Node (Error Callback)** - Connected to True Path:
   - **Method**: POST
   - **URL**: `{{ String($('Webhook').item.json.body.callback_url) }}` (**IMPORTANT**: Use `String()` to ensure proper type conversion)
   - **Body Content Type**: JSON
   - **Body**:
   ```json
   {
     "request_id": "{{ $('Webhook').item.json.body.request_id }}",
     "domain": "{{ $('Webhook').item.json.body.domain }}",
     "success": false,
     "data": null,
     "error": "{{ $json.tasks[0].status_message || $json.status_message || $json.__error?.message || 'DataForSEO API error' }}"
   }
   ```
   
   **Error Message Options:**
   - `{{ $json.tasks[0].status_message }}` - Task-specific error message
   - `{{ $json.status_message }}` - General API error message
   - `{{ $json.__error?.message }}` - N8N error message (if node execution failed)
   - Fallback: "DataForSEO API error"
   
   **Alternative simpler error expressions (try these if the above doesn't work):**
   
   **Option 1 - Simple error message:**
   ```json
   "error": "{{ $json.error.message }}"
   ```
   
   **Option 2 - Using error property:**
   ```json
   "error": "{{ $json.error }}"
   ```
   
   **Option 3 - Using string conversion:**
   ```json
   "error": "{{ String($json.__error.message) }}"
   ```
   
   **Option 4 - Check actual error structure:**
   - Click on the DataForSEO node when it errors
   - Check the OUTPUT panel to see the exact error structure
   - Use the expression editor (`</>`) to browse the error object
   - Common paths: `$json.error.message`, `$json.__error.message`, `$json.message`

**Troubleshooting URL Field:**
- If you see "Invalid URL: ``" (empty), the callback_url expression is not resolving
- **Solution**: Use `{{ $('Webhook').item.json.body.callback_url }}` (note the `.body.` part)
- The callback_url comes from the Webhook node's body property, not directly from json
- **Webhook nodes wrap POST data in a `body` property**, so always use `.body.field_name`

### 2.6 Activate Workflow

1. Click "Save" to save the workflow
2. Toggle the "Active" switch to activate the workflow
3. The webhook is now ready to receive requests

## Step 3: Test the Integration

### 3.0 Test N8N Workflow Internally (Recommended First Step)

**Before connecting to your backend, test the workflow within N8N to ensure everything works correctly.**

#### Method 1: Test Webhook Node with "Listen for Test Event"

1. **Open your workflow in N8N**
2. **Click on the Webhook node**
3. **Click the red "Listen for test event" button** (visible in the node panel)
4. **N8N will show you a test URL** like: `https://n8n.aichieve.net/webhook-test/webhook/backlinks`
5. **Send a test request** using curl or Postman:

```bash
curl -X POST https://n8n.aichieve.net/webhook-test/webhook/backlinks \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "limit": 100,
    "callback_url": "https://httpbin.org/post",
    "request_id": "test-123"
  }'
```

**Important:** Make sure you use straight quotes (`"`) not smart/curly quotes (`"` or `"`). If you get a JSON parsing error, retype the quotes manually.

**Note:** For testing, you can use `https://httpbin.org/post` as a temporary callback URL to see what N8N sends.

6. **Watch the workflow execute** in real-time in N8N
7. **Check each node's output** by clicking on it to see the data it received/processed
8. **Verify the HTTP Request node** sends the correct data to httpbin.org

#### Method 2: Execute Nodes Manually (Step by Step)

1. **Start with Webhook node:**
   - Click "Execute Node" button
   - Manually enter test data:
   ```json
   {
     "domain": "example.com",
     "limit": 100,
     "callback_url": "https://httpbin.org/post",
     "request_id": "test-123"
   }
   ```

2. **Execute DataForSEO node:**
   - Click on DataForSEO node
   - Click "Execute Node"
   - Verify it receives data from Webhook node
   - Check the output to see the structure of DataForSEO response

3. **Execute IF node:**
   - Check if error handling works correctly
   - Test both paths (success and error)

4. **Execute HTTP Request nodes:**
   - Test success callback
   - Test error callback (you can temporarily force an error)

#### Method 3: Use Mock Data

1. **Set mock data in Webhook node:**
   - Click on Webhook node
   - In the "Settings" tab, you can set mock data
   - This allows you to test without actually triggering the webhook

2. **Use Code node for testing:**
   - Add a "Code" node before DataForSEO node
   - Return mock DataForSEO response structure
   - This lets you test the rest of the workflow without API costs

#### What to Verify During Testing:

✅ **Webhook receives data correctly**
- Check that all fields (domain, limit, callback_url, request_id) are present

✅ **DataForSEO node configuration**
- Verify credentials are working
- Check the output structure matches your expressions
- Note the exact path to data (e.g., `$json.tasks[0].result[0]` or `$json`)

✅ **IF node error detection**
- Test with valid data (should go to success path)
- Test with invalid data (should go to error path)

✅ **HTTP Request nodes**
- Verify JSON structure is correct
- Check that callback_url is used correctly
- Verify request_id and domain are passed through correctly

✅ **Error handling**
- Test what happens when DataForSEO API fails
- Verify error message is captured correctly

#### Testing Checklist:

- [ ] Webhook node receives test data
- [ ] DataForSEO node executes successfully
- [ ] DataForSEO output structure is correct
- [ ] IF node routes correctly (success vs error)
- [ ] Success HTTP Request sends correct JSON
- [ ] Error HTTP Request sends correct JSON
- [ ] All expressions ({{ $json... }}) resolve correctly

#### Common Issues During Testing:

**Issue:** Expressions not resolving
- **Solution:** Check the actual output structure of previous nodes
- Use N8N's expression editor (click the `</>` icon) to browse available data

**Issue:** DataForSEO node fails
- **Solution:** Verify credentials are correct
- Check API quota/limits
- Review DataForSEO node documentation for correct operation/parameters

**Issue:** HTTP Request node fails
- **Solution:** Verify callback_url is accessible
- Check JSON structure is valid
- Ensure Content-Type header is set to `application/json`

### 3.1 Test N8N Webhook Directly (After Internal Testing)

You can test the N8N webhook using curl:

```bash
curl -X POST https://n8n.aichieve.net/webhook/backlinks \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "limit": 100,
    "callback_url": "http://your-backend-url/api/v1/n8n/webhook/backlinks",
    "request_id": "test-123"
  }'
```

### 3.2 Test from Backend

1. Start your backend application
2. Trigger a domain analysis via the API:
   ```bash
   curl -X POST http://localhost:8000/api/v1/analyze/v2 \
     -H "Content-Type: application/json" \
     -d '{"domain": "example.com"}'
   ```
3. Check the logs to see if N8N workflow was triggered
4. Monitor N8N workflow execution in N8N UI
5. Verify data was saved to database

## Step 4: Workflow JSON Template

Here's a basic workflow JSON structure you can import into N8N:

```json
{
  "name": "DataForSEO Backlinks Fetcher",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "backlinks",
        "responseMode": "responseNode",
        "options": {}
      },
      "id": "webhook-trigger",
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 1,
      "position": [250, 300],
      "webhookId": "your-webhook-id"
    },
    {
      "parameters": {
        "operation": "getBacklinks",
        "domain": "={{ $json.domain }}",
        "limit": "={{ $json.limit }}"
      },
      "id": "dataforseo-node",
      "name": "DataForSEO Backlinks",
      "type": "n8n-nodes-base.dataForSeo",
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
        "method": "POST",
        "url": "={{ $json.callback_url }}",
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "request_id",
              "value": "={{ $json.request_id }}"
            },
            {
              "name": "domain",
              "value": "={{ $json.domain }}"
            },
            {
              "name": "success",
              "value": "=true"
            },
            {
              "name": "data",
              "value": "={{ $json }}"
            }
          ]
        },
        "options": {}
      },
      "id": "http-callback",
      "name": "HTTP Request",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 1,
      "position": [650, 300]
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{"node": "DataForSEO Backlinks", "type": "main", "index": 0}]]
    },
    "DataForSEO Backlinks": {
      "main": [[{"node": "HTTP Request", "type": "main", "index": 0}]]
    }
  }
}
```

**Note**: You'll need to:
- Replace `your-webhook-id` with actual webhook ID
- Replace `your-credentials-id` with actual credentials ID
- Adjust the data mapping based on your DataForSEO node output format

## Troubleshooting

### N8N Workflow Not Triggered

- Check that `N8N_ENABLED=true` in backend `.env`
- Verify `N8N_WEBHOOK_URL` is correct and accessible
- Check N8N workflow is active
- Review backend logs for error messages

### Data Not Received in Backend

- Verify `N8N_CALLBACK_URL` is correct and accessible from N8N
- Check N8N workflow execution logs
- Verify HTTP Request node in N8N is correctly configured
- Check backend webhook endpoint logs: `/api/v1/n8n/webhook/backlinks`

### DataForSEO Node Errors

- Verify DataForSEO credentials in N8N
- Check API quota/limits in DataForSEO account
- Review DataForSEO node output format and adjust mapping

### Timeout Issues

- Increase `N8N_TIMEOUT` in backend `.env` if workflows take longer
- Check network connectivity between N8N and backend
- Review N8N workflow execution time

## N8N Workflow Implementation Guide

### Summary Data Workflow (For Testing)

If you're using **Backlinks Summary** (less expensive for testing), use this structure:

#### Success Callback JSON:
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

**Important:** Always use `$('Webhook').item.json.body.field_name` because webhook POST data is nested in the `body` property.

**Important Notes:**
- The DataForSEO node output structure is: `tasks[0].result[0]`
- For summary data, extract: `backlinks`, `referring_domains`, `rank`
- The backend will automatically normalize this structure

#### Error Callback JSON:
```json
{
  "request_id": "{{ $('Webhook').item.json.body.request_id }}",
  "domain": "{{ $('Webhook').item.json.body.domain }}",
  "success": false,
  "data": null,
  "error": "{{ $json.__error.message }}"
}
```

**Important:** Always use `$('Webhook').item.json.body.field_name` because webhook POST data is nested in the `body` property.

### Detailed Backlinks Workflow (Live Mode - Recommended)

**Note**: N8N's DataForSEO community node does NOT support async calls. Use "live" mode for all requests.

**Important**: Live mode has limitations:
- Works best for limits up to 1000-2000
- For larger limits (5000-10000), you may need to implement async manually via HTTP requests later
- For now, use live mode and set reasonable limits

**Simple Single Workflow Approach:**

#### Workflow Structure (Simplified):

```
Webhook → DataForSEO (Live) → IF (Error Check) → HTTP Request (Success/Error Callback)
```

#### Step-by-Step Implementation:

**1. Webhook Node**
- Path: `/webhook/backlinks-details`
- HTTP Method: POST
- Response Mode: "Respond When Last Node Finishes"
- Receives: `domain`, `limit`, `callback_url`, `request_id`

**2. DataForSEO Node (Live Mode)**
- **Operation**: "Get Backlinks"
- **Resource**: "Backlinks" (should be auto-selected)
- **Target (Domain)**: `{{ $('Webhook').item.json.body.domain }}`
- **Mode**: "As Is" (this is the live/synchronous mode)
- **Limit**: `{{ $('Webhook').item.json.body.limit }}` (recommended: 100-2000)
- **Include Subdomains**: Toggle ON (if needed)
- **Include Indirect Links**: Toggle ON (if needed)
- **Exclude Internal Links**: Toggle ON (recommended)
- **Backlink Status**: "Live" (recommended)
- **Rank Scale**: "0 - 100 Scale" (or your preference)
- **Filters**: Optional (e.g., `["dofollow", "=", true]`)

**Important Configuration Notes:**
- **Mode "As Is"** = Live/synchronous mode (returns immediately)
- **Limit**: Start with 100-1000 for testing, increase gradually
- **Filters**: Can be left empty or add filters like `["dofollow", "=", true]`

**3. IF Node - Error Detection**
- **Condition 1**:
  - **Value 1**: `{{ $json.status_code }}`
  - **Operation**: "Not Equal"
  - **Value 2**: `20000`
- **True Path**: Connect to HTTP Request (Error Callback)
- **False Path**: Connect to HTTP Request (Success Callback)

**4. HTTP Request Node (Success Callback)**
- **Method**: POST
- **URL**: `{{ $('Webhook').item.json.body.callback_url }}`
- **Body Content Type**: JSON
- **Body**:
```json
{
  "request_id": "{{ $('Webhook').item.json.body.request_id }}",
  "domain": "{{ $('Webhook').item.json.body.domain }}",
  "success": true,
  "data": {
    "items": {{ $json.tasks[0].result[0].items }},
    "total_count": {{ $json.tasks[0].result[0].items.length || $json.tasks[0].result[0].total_count || 0 }}
  },
  "error": null
}
```

**5. HTTP Request Node (Error Callback)**
- Same as success callback but with error data
- See error handling section below

#### Future: Async Implementation (Optional)

If you need to support larger limits (5000-10000) later, you can implement async manually:

1. **Use HTTP Request nodes** instead of DataForSEO node
2. **POST** to `/backlinks/backlinks/task_post` endpoint
3. **Poll** `/backlinks/backlinks/task_get/{task_id}` until ready
4. **GET** results when task completes

This requires more complex workflow logic but gives you full async support.

#### Success Callback JSON (Same for both approaches):
```json
{
  "request_id": "{{ $('Webhook').item.json.body.request_id }}",
  "domain": "{{ $('Webhook').item.json.body.domain }}",
  "success": true,
  "data": {
    "items": {{ $json.tasks[0].result[0].items }},
    "total_count": {{ $json.tasks[0].result[0].items.length || $json.tasks[0].result[0].total_count || 0 }}
  },
  "error": null
}
```

**Important Notes:**
- **Mode "As Is"** = Live/synchronous mode (works with N8N DataForSEO node)
- Detailed backlinks structure: `tasks[0].result[0].items[]` (array of backlink objects)
- Each item contains: `domain_from`, `url_from`, `url_to`, `anchor`, `rank`, `first_seen`, `last_seen`, etc.
- The backend expects an `items` array for detailed backlinks data
- **Cost Note**: Detailed backlinks are more expensive - use limit parameter wisely
- **Limit Recommendation**: Start with 100-1000, test performance, increase gradually
- **Async Note**: N8N DataForSEO node doesn't support async - use live mode only
- **Future**: Can implement async manually via HTTP requests if needed for larger limits

## Data Format

### Backend → N8N (Trigger)

```json
{
  "domain": "example.com",
  "limit": 10000,
  "callback_url": "http://backend/api/v1/n8n/webhook/backlinks",
  "request_id": "uuid-here"
}
```

### N8N → Backend (Callback)

**Success Response:**
```json
{
  "request_id": "uuid-here",
  "domain": "example.com",
  "success": true,
  "data": {
    "items": [...],
    "total_count": 1234
  },
  "error": null
}
```

**Error Response:**
```json
{
  "request_id": "uuid-here",
  "domain": "example.com",
  "success": false,
  "data": null,
  "error": "Error message here"
}
```

## Security Considerations

1. **Webhook Security**: Consider adding authentication to N8N webhook (API key, token)
2. **HTTPS**: Use HTTPS for production deployments
3. **Credentials**: Store DataForSEO credentials securely in N8N credentials management
4. **Network**: Ensure proper firewall rules between N8N and backend

## Advanced Configuration

### Custom Filters

You can add filters in the DataForSEO node:
- Dofollow links only
- Specific date ranges
- Domain authority thresholds
- etc.

### Retry Logic

Add retry logic in N8N workflow for failed DataForSEO requests:
1. Add **Error Trigger** node
2. Add **Wait** node for delay
3. Add **Retry** logic back to DataForSEO node

### Multiple Domains

To process multiple domains:
1. Use **Split In Batches** node after webhook
2. Process each domain separately
3. Aggregate results before callback

## Support

For issues or questions:
1. Check backend logs: `backend/src/services/n8n_service.py`
2. Check N8N workflow execution logs
3. Review webhook endpoint logs: `backend/src/api/routes/n8n_webhook.py`

