# N8N Integration Testing Guide

## Pre-Testing Checklist

Before testing from the frontend, verify these steps:

### ✅ Step 1: Verify ngrok is Running

```bash
# Check ngrok status
# Should show: "Session Status: online"
# Note the Forwarding URL (e.g., https://abc123.ngrok-free.dev)
```

### ✅ Step 2: Update Backend .env

Make sure `backend/.env` has:

```bash
N8N_ENABLED=true
N8N_WEBHOOK_URL=https://n8n.aichieve.net/webhook/webhook/backlinks-details
N8N_CALLBACK_URL=https://YOUR-NGROK-URL.ngrok-free.dev/api/v1/n8n/webhook/backlinks
N8N_TIMEOUT=60
N8N_USE_FOR_BACKLINKS=true
```

**Important**: Replace `YOUR-NGROK-URL` with your actual ngrok URL.

### ✅ Step 3: Update N8N Workflow

In your N8N workflow, the HTTP Request node (callback) should have:

- **URL**: `{{ $('Webhook').item.json.body.callback_url }}`
- Or hardcode: `https://YOUR-NGROK-URL.ngrok-free.dev/api/v1/n8n/webhook/backlinks`

### ✅ Step 4: Verify Backend Server is Running

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test N8N webhook endpoint locally
curl -X POST http://localhost:8000/api/v1/n8n/webhook/backlinks \
  -H "Content-Type: application/json" \
  -d '{"request_id":"test","domain":"test.com","success":true,"data":{"items":[]},"error":null}'
```

### ✅ Step 5: Verify N8N Workflow is Active

- Go to N8N: https://n8n.aichieve.net
- Check your workflow is **Active** (toggle should be ON)
- Verify webhook path: `/webhook/webhook/backlinks-details`

## Testing Sequence

### Option 1: Test from Frontend (Recommended for Full Integration)

1. **Open your frontend** (usually http://localhost:3000 or similar)

2. **Start a domain analysis:**
   - Enter a test domain (e.g., "example.com")
   - Click "Analyze" or "Start Analysis"

3. **Monitor the process:**
   - **Frontend**: Should show progress updates
   - **Backend logs**: Should show "Triggering N8N workflow..."
   - **N8N workflow**: Should execute (check N8N UI)
   - **Backend logs**: Should show "N8N backlinks data received via webhook"

4. **Verify results:**
   - Check if analysis completes
   - Verify backlinks data is displayed in frontend
   - Check database to confirm data was saved

### Option 2: Test N8N Workflow Directly First

Before testing from frontend, you can test the N8N workflow directly:

```bash
# Test N8N webhook trigger
curl -X POST https://n8n.aichieve.net/webhook/webhook/backlinks-details \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "limit": 100,
    "callback_url": "https://YOUR-NGROK-URL.ngrok-free.dev/api/v1/n8n/webhook/backlinks",
    "request_id": "test-123"
  }'
```

Then:
1. Watch N8N workflow execute
2. Check if it calls back to your backend
3. Verify backend receives the data

## What to Monitor During Testing

### Backend Logs

Look for these log messages:

```
✅ "Triggering N8N workflow for backlinks"
✅ "N8N workflow triggered successfully"
✅ "N8N workflow triggered, waiting for callback"
✅ "N8N backlinks data received via webhook"
✅ "N8N backlinks data saved successfully"
```

### N8N Workflow

1. Go to N8N UI: https://n8n.aichieve.net
2. Open your workflow
3. Check "Executions" tab
4. Verify:
   - Webhook received the request
   - DataForSEO node executed successfully
   - HTTP Request (callback) sent data to backend

### Frontend

- Progress indicators should update
- Analysis should complete
- Backlinks data should be visible

## Troubleshooting

### Issue: Backend doesn't trigger N8N

**Check:**
- `N8N_ENABLED=true` in `.env`
- `N8N_WEBHOOK_URL` is correct
- Backend can reach N8N (test with curl)

**Solution:**
```bash
# Test N8N webhook from backend location
curl -X POST https://n8n.aichieve.net/webhook/webhook/backlinks-details \
  -H "Content-Type: application/json" \
  -d '{"domain":"test.com","limit":100,"callback_url":"https://httpbin.org/post","request_id":"test"}'
```

### Issue: N8N doesn't call back

**Check:**
- ngrok is running and URL is correct
- `N8N_CALLBACK_URL` in `.env` matches ngrok URL
- N8N workflow has correct callback URL
- Backend webhook endpoint is accessible via ngrok

**Solution:**
```bash
# Test backend webhook via ngrok
curl -X POST https://YOUR-NGROK-URL.ngrok-free.dev/api/v1/n8n/webhook/backlinks \
  -H "Content-Type: application/json" \
  -d '{"request_id":"test","domain":"test.com","success":true,"data":{"items":[]},"error":null}'
```

### Issue: Timeout waiting for N8N

**Check:**
- N8N workflow execution time
- Increase `N8N_TIMEOUT` in `.env` if needed
- Check N8N workflow logs for errors

**Solution:**
```bash
# Increase timeout in .env
N8N_TIMEOUT=120  # 2 minutes
```

### Issue: Data not received

**Check:**
- N8N workflow executed successfully
- HTTP Request node in N8N sent data
- Backend webhook endpoint received request
- Database connection is working

**Solution:**
- Check N8N execution logs
- Check backend logs for webhook reception
- Verify database has the data

## Expected Flow

```
1. Frontend → Backend: POST /api/v1/analyze/v2
   ↓
2. Backend → N8N: POST https://n8n.aichieve.net/webhook/backlinks-details
   ↓
3. N8N → DataForSEO: Get backlinks
   ↓
4. N8N → Backend: POST https://ngrok-url/api/v1/n8n/webhook/backlinks
   ↓
5. Backend saves data to database
   ↓
6. Backend continues analysis (keywords, AI, etc.)
   ↓
7. Frontend receives completed analysis
```

## Success Criteria

✅ Frontend triggers analysis successfully
✅ Backend logs show N8N workflow triggered
✅ N8N workflow executes and completes
✅ Backend receives backlinks data via webhook
✅ Analysis completes with backlinks data
✅ Frontend displays backlinks in the UI

## Next Steps After Successful Test

1. **Monitor costs**: Check DataForSEO usage in N8N
2. **Optimize limits**: Adjust limit based on needs
3. **Production setup**: Deploy backend to same server as N8N
4. **Remove ngrok**: Use direct HTTPS URLs in production



























