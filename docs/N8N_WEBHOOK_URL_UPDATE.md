# N8N Webhook URL Update

## Issue
The backend was calling incorrect webhook URLs:
- ❌ Wrong: `https://n8n.aichieve.net/webhook-test/webhook/backlinks-details`
- ✅ Correct: `https://n8n.aichieve.net/webhook/backlinks-details-single-page`

## Solution

Update your `backend/.env` file with the correct webhook URLs:

```bash
# N8N Integration Settings
N8N_ENABLED=true

# Summary Backlinks Workflow (Single Page)
N8N_WEBHOOK_URL_SUMMARY=https://n8n.aichieve.net/webhook/backlinks-summary-single-page

# Detailed Backlinks Workflow (Single Page)
N8N_WEBHOOK_URL=https://n8n.aichieve.net/webhook/backlinks-details-single-page

# Callback URL (base URL - backend will append /backlinks or /backlinks-summary)
N8N_CALLBACK_URL=https://your-backend-url/api/v1/n8n/webhook/backlinks
N8N_TIMEOUT=60
N8N_USE_FOR_BACKLINKS=true
N8N_USE_FOR_SUMMARY=true
```

## Workflow Paths

The workflow file has been updated to use:
- **Summary webhook path**: `backlinks-summary-single-page`
- **Details webhook path**: `backlinks-details-single-page`

These paths create the full URLs:
- `https://n8n.aichieve.net/webhook/backlinks-summary-single-page`
- `https://n8n.aichieve.net/webhook/backlinks-details-single-page`

## After Updating

1. **Update `.env` file** with the correct URLs above
2. **Restart backend server** to load new configuration
3. **Verify workflow paths in N8N** match the updated paths
4. **Test the analysis** again

## Verification

After updating, check the logs to confirm the correct URLs are being used:

```bash
# Should see:
"webhook_url": "https://n8n.aichieve.net/webhook/backlinks-summary-single-page"
"webhook_url": "https://n8n.aichieve.net/webhook/backlinks-details-single-page"
```


