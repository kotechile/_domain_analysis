# Troubleshooting: "Failed to trigger N8N summary workflow"

## Error Message
```
Failed to trigger N8N summary workflow
```

## Root Causes

This error occurs when the backend cannot successfully trigger the N8N summary workflow. The `trigger_backlinks_summary_workflow()` method returns `None` in these cases:

### 1. Missing Configuration (Most Common)

**Check your `backend/.env` file has:**

```bash
# Required for summary workflow
N8N_ENABLED=true
N8N_WEBHOOK_URL_SUMMARY=https://n8n.aichieve.net/webhook/webhook/backlinks-summary
N8N_CALLBACK_URL=https://your-backend-url/api/v1/n8n/webhook/backlinks
N8N_USE_FOR_SUMMARY=true
```

**Missing any of these will cause the failure.**

### 2. Webhook Path Mismatch

Your workflow file has the webhook path as `backlinks-summary`, which creates the URL:
```
https://n8n.aichieve.net/webhook/backlinks-summary
```

**But your `.env` might be configured for:**
```
https://n8n.aichieve.net/webhook/webhook/backlinks-summary
```

**Solution Options:**

**Option A: Update Workflow Path (Recommended)**
1. Open the workflow in N8N
2. Change the Webhook (Summary) node path from `backlinks-summary` to `webhook/backlinks-summary`
3. Save and activate the workflow
4. Update `.env`:
   ```bash
   N8N_WEBHOOK_URL_SUMMARY=https://n8n.aichieve.net/webhook/webhook/backlinks-summary
   ```

**Option B: Update .env to Match Workflow**
Keep workflow path as `backlinks-summary` and update `.env`:
```bash
N8N_WEBHOOK_URL_SUMMARY=https://n8n.aichieve.net/webhook/backlinks-summary
```

### 3. Workflow Not Active

**Check in N8N:**
1. Open the "DataForSEO Backlinks Single Page" workflow
2. Ensure the **green toggle** is ON (workflow is active)
3. If inactive, click the toggle to activate
4. Wait a few seconds for N8N to register the webhook

### 4. N8N Server Unreachable

**Test if N8N is accessible:**
```bash
curl -X POST https://n8n.aichieve.net/webhook/backlinks-summary \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "test.com",
    "callback_url": "https://httpbin.org/post",
    "request_id": "test-123",
    "type": "summary"
  }'
```

**Expected**: HTTP 200 response
**If 404**: Webhook path is wrong or workflow not active
**If timeout**: N8N server might be down

### 5. Missing Callback URL

The backend needs `N8N_CALLBACK_URL` to construct the callback URL for N8N.

**Check:**
```bash
# In backend/.env
N8N_CALLBACK_URL=https://your-backend-url/api/v1/n8n/webhook/backlinks
```

**For local development**, use ngrok:
```bash
# Start ngrok
ngrok http 8000

# Copy the HTTPS URL and update .env
N8N_CALLBACK_URL=https://abc123.ngrok-free.dev/api/v1/n8n/webhook/backlinks
```

## Quick Diagnostic Steps

1. **Check backend logs** for detailed error:
   ```bash
   # Look for these log messages:
   - "N8N summary integration is disabled" → N8N_USE_FOR_SUMMARY=false
   - "N8N callback URL not configured" → Missing N8N_CALLBACK_URL
   - "N8N summary workflow trigger failed" → HTTP request failed
   - "status_code: 404" → Webhook path wrong or workflow inactive
   ```

2. **Verify N8N configuration**:
   ```bash
   # Check if summary is enabled
   grep N8N_USE_FOR_SUMMARY backend/.env
   # Should be: N8N_USE_FOR_SUMMARY=true
   
   # Check webhook URL
   grep N8N_WEBHOOK_URL_SUMMARY backend/.env
   # Should match your N8N workflow webhook URL
   ```

3. **Test N8N webhook directly**:
   ```bash
   curl -X POST https://n8n.aichieve.net/webhook/backlinks-summary \
     -H "Content-Type: application/json" \
     -d '{"domain":"test.com","callback_url":"https://httpbin.org/post","request_id":"test","type":"summary"}'
   ```

## Complete Fix Checklist

- [ ] `N8N_ENABLED=true` in `.env`
- [ ] `N8N_WEBHOOK_URL_SUMMARY` is set and matches N8N workflow path
- [ ] `N8N_CALLBACK_URL` is set and accessible from N8N
- [ ] `N8N_USE_FOR_SUMMARY=true` in `.env`
- [ ] Workflow is **Active** (green toggle ON) in N8N
- [ ] Webhook path in workflow matches URL in `.env`
- [ ] Backend server restarted after `.env` changes
- [ ] N8N server is accessible (test with curl)

## Expected Backend Logs (Success)

When working correctly, you should see:
```
INFO: Using N8N for backlinks summary, domain=giniloh.com
INFO: Triggering N8N workflow for backlinks summary, domain=giniloh.com, request_id=...
INFO: N8N summary workflow triggered successfully, domain=giniloh.com, status_code=200
INFO: N8N summary workflow triggered, waiting for callback, domain=giniloh.com, request_id=...
```

## Next Steps After Fix

1. Restart backend server
2. Try analyzing the domain again
3. Check N8N execution logs to see if workflow ran
4. Check backend webhook endpoint logs to see if callback was received


