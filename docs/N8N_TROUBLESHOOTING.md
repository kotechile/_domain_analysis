# N8N Troubleshooting Guide

## Issue: Webhooks Not Triggering N8N

### Common Causes

1. **Invalid Callback URL** (Most Common)
   - `.env` has placeholder: `N8N_CALLBACK_URL=https://YOUR-NGROK-URL.ngrok-free.dev/...`
   - **Fix**: Update with actual ngrok URL

2. **N8N Not Enabled**
   - Check: `N8N_ENABLED=true` in `.env`
   - Check: Backend logs show "N8N integration is disabled"

3. **Webhook URL Incorrect**
   - Check: `N8N_WEBHOOK_URL` matches actual N8N webhook URL
   - Test: `curl -X POST https://n8n.aichieve.net/webhook/webhook/backlinks-details ...`

4. **Backend Not Restarted**
   - After changing `.env`, backend must be restarted
   - Environment variables are loaded at startup

## Quick Fix Steps

### Step 1: Get Your ngrok URL

```bash
# Check ngrok status
curl http://localhost:4040/api/tunnels

# Or check ngrok terminal for the URL
# Should show: https://abc123.ngrok-free.dev
```

### Step 2: Update .env File

```bash
# Edit backend/.env
N8N_CALLBACK_URL=https://YOUR-ACTUAL-NGROK-URL.ngrok-free.dev/api/v1/n8n/webhook/backlinks
```

Replace `YOUR-ACTUAL-NGROK-URL` with your actual ngrok URL.

### Step 3: Restart Backend

```bash
# Kill existing backend
lsof -ti:8000 | xargs kill

# Restart backend
cd backend
source venv/bin/activate
python run_server.py
```

### Step 4: Verify Configuration

Check backend logs for:
```
N8N integration is enabled
N8N_WEBHOOK_URL=https://n8n.aichieve.net/webhook/webhook/backlinks-details
N8N_CALLBACK_URL=https://your-ngrok-url/api/v1/n8n/webhook/backlinks
```

## Debugging

### Check if N8N Service is Enabled

Add this to your backend code temporarily:
```python
from services.n8n_service import N8NService
n8n = N8NService()
print(f"N8N Enabled: {n8n.enabled}")
print(f"N8N Webhook URL: {n8n.settings.N8N_WEBHOOK_URL}")
print(f"N8N Callback URL: {n8n.settings.N8N_CALLBACK_URL}")
```

### Test N8N Webhook Directly

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

If this works, N8N is fine - the issue is backend configuration.

### Check Backend Logs

When triggering analysis, look for:
```
Triggering N8N workflow for backlinks
N8N workflow triggered successfully
```

If you see:
```
N8N integration is disabled
```
→ Check `N8N_ENABLED=true` in `.env`

If you see:
```
N8N callback URL not configured
```
→ Check `N8N_CALLBACK_URL` in `.env`

If you see:
```
N8N workflow trigger failed
```
→ Check `N8N_WEBHOOK_URL` is correct and N8N is accessible

## Removed Fallback Logic

The misleading fallback to direct DataForSEO API has been removed. Now:
- If N8N is enabled but fails → **Error is raised** (not silent fallback)
- If N8N is enabled but times out → **Error is raised** (not silent fallback)

This ensures you know immediately if N8N is not working, rather than silently falling back to an API that doesn't work for your account.























