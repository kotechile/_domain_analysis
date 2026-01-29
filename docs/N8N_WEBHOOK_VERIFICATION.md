# N8N Webhook Verification Guide

## Quick Check: Are Your Workflows Ready?

Just because workflows are **Active** doesn't mean they're ready to receive backend calls. You need to verify:

1. ✅ **Workflow is Active** (green toggle) - You have this!
2. ✅ **Webhook node is configured** - Need to verify
3. ✅ **Webhook has Production URL** - Need to verify
4. ✅ **Webhook path matches backend config** - Need to verify

## Step-by-Step Verification

### 1. Check Webhook Nodes in Each Workflow

For **each** workflow (Summary and Details):

1. **Open the workflow** in N8N
2. **Find the Webhook node** (should be the first node)
3. **Click on the Webhook node** to open its settings
4. **Check these settings:**

#### Webhook Node Settings:

- **HTTP Method**: Should be `POST`
- **Path**: Should match your backend configuration:
  - Summary: `/webhook/backlinks-summary` (or similar)
  - Details: `/webhook/backlinks-details` (or similar)
- **Response Mode**: `Last Node` or `When Last Node Finishes`
- **Production URL**: Should show a URL like:
  - `https://n8n.aichieve.net/webhook/webhook/backlinks-summary`
  - `https://n8n.aichieve.net/webhook/webhook/backlinks-details`

### 2. Verify Production URLs Match Backend Config

Your backend `.env` should have:

```bash
N8N_WEBHOOK_URL_SUMMARY=https://n8n.aichieve.net/webhook/webhook/backlinks-summary
N8N_WEBHOOK_URL=https://n8n.aichieve.net/webhook/webhook/backlinks-details
```

**Check:**
- Do the Production URLs in N8N match these paths?
- Are they using `https://` (not `http://`)?
- Do they match exactly (including `/webhook/webhook/` prefix)?

### 3. Test Webhook Directly

You can test if the webhooks are accessible:

```bash
# Test Summary Webhook
curl -X POST https://n8n.aichieve.net/webhook/webhook/backlinks-summary \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "test.com",
    "callback_url": "https://httpbin.org/post",
    "request_id": "test-123",
    "type": "summary"
  }'

# Test Details Webhook
curl -X POST https://n8n.aichieve.net/webhook/webhook/backlinks-details \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "test.com",
    "limit": 100,
    "callback_url": "https://httpbin.org/post",
    "request_id": "test-456",
    "type": "detailed"
  }'
```

**Expected Response:**
- If webhook is working: You should see a response from N8N (might be empty `{}` or workflow execution info)
- If webhook is NOT working: You'll get a 404 or error

### 4. Check Workflow Execution

After testing with curl:

1. Go to N8N dashboard
2. Click on **"Executions"** tab
3. You should see new executions from your test
4. Click on an execution to see if it ran successfully

## Common Issues

### Issue 1: "Production URL is empty"

**Problem**: Webhook node shows empty Production URL

**Solution**:
1. Make sure workflow is **saved** (Ctrl+S or Cmd+S)
2. Make sure workflow is **Active** (green toggle)
3. Refresh the webhook node settings
4. Production URL should appear after saving and activating

### Issue 2: "Webhook path doesn't match"

**Problem**: Production URL path doesn't match backend config

**Example**:
- Backend expects: `/webhook/webhook/backlinks-summary`
- N8N shows: `/webhook/backlinks-summary` (missing `/webhook/`)

**Solution**:
- Update the webhook node **Path** to match exactly
- Or update backend `.env` to match N8N's actual path

### Issue 3: "Webhook returns 404"

**Problem**: curl test returns 404 Not Found

**Possible Causes**:
1. Workflow is not Active
2. Webhook node path is incorrect
3. Webhook node is not saved
4. N8N service is not running

**Solution**:
1. Verify workflow is Active (green toggle)
2. Check webhook node path matches the URL you're calling
3. Save the workflow again
4. Check N8N service status in Coolify

### Issue 4: "Workflow executes but doesn't call back"

**Problem**: Workflow runs but doesn't send data to backend

**Check**:
1. HTTP Request node (callback) is configured correctly
2. Callback URL expression: `{{ $('Webhook').item.json.body.callback_url }}`
3. HTTP Request method is `POST`
4. HTTP Request sends JSON body with correct structure

## Verification Checklist

Before testing from backend:

- [ ] Both workflows are **Active** (green toggle)
- [ ] Both workflows have **Webhook nodes** as first node
- [ ] Webhook nodes have **Production URLs** (not empty)
- [ ] Production URLs match backend `.env` configuration
- [ ] Webhook nodes use **POST** method
- [ ] Test with curl returns success (not 404)
- [ ] Workflow executions appear in N8N after curl test
- [ ] HTTP Request nodes (callbacks) are configured correctly

## Next Steps

Once verified:

1. ✅ Update `backend/.env` with correct webhook URLs
2. ✅ Start ngrok and update `N8N_CALLBACK_URL`
3. ✅ Restart backend server
4. ✅ Test from frontend

## Quick Test Command

Run this to test both webhooks at once:

```bash
echo "Testing Summary Webhook..."
curl -X POST https://n8n.aichieve.net/webhook/webhook/backlinks-summary \
  -H "Content-Type: application/json" \
  -d '{"domain":"test.com","callback_url":"https://httpbin.org/post","request_id":"test-summary","type":"summary"}' \
  -w "\nStatus: %{http_code}\n"

echo -e "\nTesting Details Webhook..."
curl -X POST https://n8n.aichieve.net/webhook/webhook/backlinks-details \
  -H "Content-Type: application/json" \
  -d '{"domain":"test.com","limit":100,"callback_url":"https://httpbin.org/post","request_id":"test-details","type":"detailed"}' \
  -w "\nStatus: %{http_code}\n"
```

**Expected**: Both should return `Status: 200` or `Status: 201`



























