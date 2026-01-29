# N8N Backend Integration Guide

## Overview

This guide covers integrating N8N (running on Hostinger/Coolify) with your backend/frontend (running locally).

## Current Backend Implementation

✅ **Already Implemented:**
- N8N service integration
- Automatic fallback to direct DataForSEO API if N8N fails
- Webhook endpoint to receive N8N callbacks
- Database polling to wait for N8N results

✅ **No Need to Disable Current Calls:**
- The backend has **automatic fallback** logic
- If N8N is disabled or fails, it automatically uses direct DataForSEO API
- You can enable/disable N8N via environment variables

## Integration Steps

### Step 1: Make Your Local Backend Accessible to N8N

**Problem**: N8N is on Hostinger, your backend is local. N8N needs to call back to your backend.

**Solution Options:**

#### Option A: Use ngrok (Recommended for Development)

1. **Install ngrok:**
   ```bash
   # macOS
   brew install ngrok
   
   # Or download from https://ngrok.com/
   ```

2. **Start ngrok tunnel:**
   ```bash
   ngrok http 8000
   ```

3. **Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)

4. **Use this URL in your backend `.env`:**
   ```bash
   N8N_CALLBACK_URL=https://abc123.ngrok.io/api/v1/n8n/webhook/backlinks
   ```

**Note**: ngrok URLs change each time you restart. For production, use Option B or C.

#### Option B: Deploy Backend to Same Server (Recommended for Production)

Deploy your backend to the same Hostinger server where N8N runs:
- Backend accessible at: `https://api.aichieve.net` (or similar)
- N8N can call: `https://api.aichieve.net/api/v1/n8n/webhook/backlinks`

#### Option C: Use Cloudflare Tunnel or Similar

Set up a persistent tunnel to expose your local backend.

### Step 2: Configure Backend Environment Variables

Add to your `backend/.env` file:

```bash
# N8N Integration Settings
N8N_ENABLED=true
N8N_WEBHOOK_URL=https://n8n.aichieve.net/webhook/webhook/backlinks-details
N8N_CALLBACK_URL=https://your-ngrok-url.ngrok.io/api/v1/n8n/webhook/backlinks
N8N_TIMEOUT=60
N8N_USE_FOR_BACKLINKS=true
```

**Important:**
- `N8N_WEBHOOK_URL`: Your N8N webhook URL (from N8N workflow)
- `N8N_CALLBACK_URL`: Must be accessible from N8N (use ngrok for local dev)
- `N8N_ENABLED`: Set to `false` to disable N8N and use direct API

### Step 3: Verify Network Connectivity

**Test 1: Backend → N8N (Trigger)**
```bash
# From your local machine, test if you can reach N8N
curl -X POST https://n8n.aichieve.net/webhook/webhook/backlinks-details \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "limit": 100,
    "callback_url": "https://your-ngrok-url.ngrok.io/api/v1/n8n/webhook/backlinks",
    "request_id": "test-123"
  }'
```

**Test 2: N8N → Backend (Callback)**
```bash
# Test if N8N can reach your backend (from N8N's perspective)
# Use httpbin.org to test first, then your actual callback URL
```

### Step 4: Test the Integration

1. **Start your backend locally:**
   ```bash
   cd backend
   python -m uvicorn src.main:app --reload
   ```

2. **Start ngrok** (if using Option A):
   ```bash
   ngrok http 8000
   ```

3. **Update `.env` with ngrok URL** (if using Option A)

4. **Trigger an analysis:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/analyze/v2 \
     -H "Content-Type: application/json" \
     -d '{"domain": "example.com"}'
   ```

5. **Monitor logs:**
   - Backend logs: Should show "Triggering N8N workflow..."
   - N8N workflow: Should execute and call back
   - Backend logs: Should show "N8N backlinks data received via webhook"

## How It Works

### Flow Diagram:

```
1. Frontend → Backend API: POST /api/v1/analyze/v2
2. Backend → N8N Webhook: POST https://n8n.aichieve.net/webhook/backlinks-details
3. N8N → DataForSEO API: Get backlinks
4. N8N → Backend Webhook: POST https://your-backend/api/v1/n8n/webhook/backlinks
5. Backend saves data to database
6. Backend continues analysis (keywords, AI, etc.)
```

### Automatic Fallback:

The backend has built-in fallback logic:

1. **If N8N_ENABLED=false**: Uses direct DataForSEO API
2. **If N8N trigger fails**: Falls back to direct DataForSEO API
3. **If N8N timeout (120s)**: Falls back to direct DataForSEO API
4. **If N8N callback fails**: Backend still has data from polling

**You don't need to disable anything** - it's all automatic!

## Configuration Options

### Enable/Disable N8N

**To use N8N:**
```bash
N8N_ENABLED=true
N8N_USE_FOR_BACKLINKS=true
```

**To use direct API (disable N8N):**
```bash
N8N_ENABLED=false
# Or
N8N_USE_FOR_BACKLINKS=false
```

### Adjust Timeout

If N8N workflows take longer:
```bash
N8N_TIMEOUT=120  # Increase to 2 minutes
```

### Adjust Polling

The backend polls the database every 2 seconds for up to 120 seconds. This is hardcoded in `analysis_service.py` but can be adjusted if needed.

## Troubleshooting

### Issue: N8N can't reach backend callback URL

**Symptoms:**
- N8N workflow executes but callback fails
- Backend times out waiting for data

**Solutions:**
1. **Check ngrok is running** (if using ngrok)
2. **Verify callback URL is correct** in `.env`
3. **Test callback URL manually:**
   ```bash
   curl -X POST https://your-ngrok-url.ngrok.io/api/v1/n8n/webhook/backlinks \
     -H "Content-Type: application/json" \
     -d '{
       "request_id": "test",
       "domain": "example.com",
       "success": true,
       "data": {"items": []},
       "error": null
     }'
   ```

### Issue: Backend can't reach N8N

**Symptoms:**
- "N8N workflow trigger failed" in logs
- Timeout errors

**Solutions:**
1. **Verify N8N_WEBHOOK_URL is correct**
2. **Check N8N workflow is active**
3. **Test N8N webhook directly:**
   ```bash
   curl -X POST https://n8n.aichieve.net/webhook/webhook/backlinks-details \
     -H "Content-Type: application/json" \
     -d '{"domain": "test.com", "limit": 100, "callback_url": "https://httpbin.org/post", "request_id": "test"}'
   ```

### Issue: Data not received

**Symptoms:**
- N8N workflow completes but backend doesn't receive data
- Backend falls back to direct API

**Solutions:**
1. **Check N8N workflow execution logs**
2. **Verify callback URL in N8N workflow**
3. **Check backend webhook endpoint logs**
4. **Verify database connection** (data is saved to database)

## Production Deployment

### Recommended Setup:

1. **Deploy backend to same server as N8N:**
   - Backend: `https://api.aichieve.net`
   - N8N: `https://n8n.aichieve.net`

2. **Update environment variables:**
   ```bash
   N8N_ENABLED=true
   N8N_WEBHOOK_URL=https://n8n.aichieve.net/webhook/webhook/backlinks-details
   N8N_CALLBACK_URL=https://api.aichieve.net/api/v1/n8n/webhook/backlinks
   N8N_TIMEOUT=60
   N8N_USE_FOR_BACKLINKS=true
   ```

3. **Both services can communicate via HTTPS**

## Summary

✅ **What's Already Done:**
- Backend N8N integration code
- Automatic fallback logic
- Webhook endpoint
- Database polling

✅ **What You Need to Do:**
1. Configure environment variables
2. Make backend accessible to N8N (ngrok for dev, deploy for prod)
3. Test the integration
4. Monitor and adjust as needed

✅ **No Need To:**
- Disable current backlinks calls (automatic fallback handles it)
- Modify code (everything is already implemented)
- Change frontend (transparent to frontend)

The integration is **opt-in via environment variables** - you can enable/disable it anytime!



























