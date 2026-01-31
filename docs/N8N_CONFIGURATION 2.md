# N8N Configuration Guide

## Architecture Overview

Your backend uses DataForSEO APIs through N8N for **both** Summary and Detailed backlinks:

### Phase 1: Essential Data (Summary) - **USES N8N**
- **Method**: `_collect_essential_data()`
- **API Call**: N8N workflow → DataForSEO Summary API
- **Purpose**: Get totals (`total_backlinks`, `total_referring_domains`, `rank`)
- **N8N Integration**: ✅ **USED** - Backend triggers N8N summary workflow
- **Fallback**: If N8N fails, falls back to direct DataForSEO API (but this will fail if API is disabled)

### Phase 2: Detailed Data (Individual Backlinks) - **USES N8N**
- **Method**: `_collect_detailed_data()`
- **API Call**: N8N workflow → DataForSEO Detailed Backlinks API
- **Purpose**: Get individual backlink records for quality analysis
- **N8N Integration**: ✅ **USED** - Backend triggers N8N detailed workflow
- **Fallback**: If N8N fails, falls back to direct DataForSEO API (but this will fail if API is disabled)

## Configuration

### Backend `.env` File

Add these variables to `backend/.env`:

```bash
# N8N Integration Settings
N8N_ENABLED=true

# Summary Backlinks Workflow
N8N_WEBHOOK_URL_SUMMARY=https://n8n.aichieve.net/webhook/webhook/backlinks

# Detailed Backlinks Workflow
N8N_WEBHOOK_URL=https://n8n.aichieve.net/webhook/webhook/backlinks-details

# Callback URL (base URL - backend will append /backlinks or /backlinks-summary)
N8N_CALLBACK_URL=https://YOUR-NGROK-URL.ngrok-free.dev/api/v1/n8n/webhook/backlinks
N8N_TIMEOUT=60
N8N_USE_FOR_BACKLINKS=true
N8N_USE_FOR_SUMMARY=true
```

**Important Notes:**
1. **N8N_WEBHOOK_URL_SUMMARY**: Your N8N workflow webhook for **summary backlinks**
2. **N8N_WEBHOOK_URL**: Your N8N workflow webhook for **detailed backlinks**
3. **N8N_CALLBACK_URL**: Base callback URL - backend will automatically use:
   - `/api/v1/n8n/webhook/backlinks-summary` for summary callbacks
   - `/api/v1/n8n/webhook/backlinks` for detailed callbacks
4. **For Local Development**: Use ngrok to expose your local backend:
   ```bash
   # Install ngrok: brew install ngrok
   # Start tunnel: ngrok http 8000
   # Use the ngrok HTTPS URL for N8N_CALLBACK_URL
   N8N_CALLBACK_URL=https://abc123.ngrok.io/api/v1/n8n/webhook/backlinks
   ```

### Get Your ngrok URL

1. Start ngrok in a terminal:
   ```bash
   ngrok http 8000
   ```

2. Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.dev`)

3. Update `N8N_CALLBACK_URL` in `.env`:
   ```bash
   N8N_CALLBACK_URL=https://abc123.ngrok-free.dev/api/v1/n8n/webhook/backlinks
   ```

## N8N Workflow Requirements

### Workflow 1: Summary Backlinks (`/webhook/webhook/backlinks`)

Your N8N workflow should:

1. **Receive webhook** with:
   ```json
   {
     "domain": "example.com",
     "callback_url": "https://ngrok-url/api/v1/n8n/webhook/backlinks-summary",
     "request_id": "uuid",
     "type": "summary"
   }
   
   **Note**: The webhook URL is `/webhook/webhook/backlinks` (not `/backlinks-summary`)
   ```

2. **Call DataForSEO** "Get Backlinks Summary"
   - **Operation**: "Get Backlinks Summary"
   - **Resource**: "Backlinks Summary" or "Summary"
   - **Mode**: "live"
   - **Target**: `{{ $('Webhook').item.json.body.domain }}`

3. **Send results back** to `callback_url`:
   ```json
   {
     "request_id": "uuid",
     "domain": "example.com",
     "success": true,
     "data": {
       "backlinks": 1234,
       "referring_domains": 567,
       "rank": 36,
       "first_seen": "2020-09-25 01:08:18 +00:00",
       ...
     },
     "error": null
   }
   ```

### Workflow 2: Detailed Backlinks (`/webhook/webhook/backlinks-details`)

Your N8N workflow should:

1. **Receive webhook** with:
   ```json
   {
     "domain": "example.com",
     "limit": 10000,
     "callback_url": "https://ngrok-url/api/v1/n8n/webhook/backlinks",
     "request_id": "uuid",
     "type": "detailed"
   }
   ```

2. **Call DataForSEO** "Get Backlinks" (detailed, not summary)
   - **Operation**: "Get Backlinks"
   - **Resource**: "Backlinks"
   - **Mode**: "live" (since async not supported in N8N community node)
   - **Limit**: Use `{{ $('Webhook').item.json.body.limit }}`

3. **Send results back** to `callback_url`:
   ```json
   {
     "request_id": "uuid",
     "domain": "example.com",
     "success": true,
     "data": {
       "items": [...],  // Array of backlink objects
       "total_count": 1234
     },
     "error": null
   }
   ```

## Data Flow

```
1. Frontend → Backend: POST /api/v1/analyze/v2
   ↓
2. Backend → N8N: POST /webhook/backlinks-summary (trigger summary)
   ↓
3. N8N → DataForSEO: Get summary
   ↓
4. N8N → Backend: POST /api/v1/n8n/webhook/backlinks-summary (send summary results)
   ↓
5. Backend → N8N: POST /webhook/backlinks-details (trigger detailed backlinks)
   ↓
6. N8N → DataForSEO: Get detailed backlinks
   ↓
7. N8N → Backend: POST /api/v1/n8n/webhook/backlinks (send detailed results)
   ↓
8. Backend continues analysis (keywords, AI, etc.)
   ↓
9. Frontend receives completed analysis
```

## Verification

### Test Backend Configuration

```bash
# Test summary webhook
curl -X POST https://n8n.aichieve.net/webhook/webhook/backlinks \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "test.com",
    "callback_url": "https://httpbin.org/post",
    "request_id": "test-123",
    "type": "summary"
  }'

# Test detailed webhook
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

### Test Backend Webhooks

```bash
# Test summary webhook endpoint
curl -X POST https://YOUR-NGROK-URL.ngrok-free.dev/api/v1/n8n/webhook/backlinks-summary \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test",
    "domain": "test.com",
    "success": true,
    "data": {
      "backlinks": 100,
      "referring_domains": 50,
      "rank": 30
    },
    "error": null
  }'

# Test detailed webhook endpoint
curl -X POST https://YOUR-NGROK-URL.ngrok-free.dev/api/v1/n8n/webhook/backlinks \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test",
    "domain": "test.com",
    "success": true,
    "data": {
      "items": [],
      "total_count": 0
    },
    "error": null
  }'
```

## Troubleshooting

### Issue: Backend doesn't trigger N8N for summary

**Check:**
- `N8N_ENABLED=true` in `.env`
- `N8N_WEBHOOK_URL_SUMMARY` is correct
- `N8N_USE_FOR_SUMMARY=true` in `.env`
- Backend logs show "Using N8N for backlinks summary"

**Solution:**
- Restart backend after changing `.env`
- Check backend logs for errors

### Issue: N8N doesn't call back

**Check:**
- ngrok is running
- `N8N_CALLBACK_URL` matches ngrok URL
- N8N workflow uses `{{ $('Webhook').item.json.body.callback_url }}`
- Backend webhook endpoints are accessible

**Solution:**
- Verify ngrok URL is correct
- Test webhook endpoints directly
- Check N8N workflow execution logs

### Issue: Timeout waiting for N8N

**Check:**
- N8N workflow execution time
- Increase `N8N_TIMEOUT` if needed
- Check if DataForSEO API is slow

**Solution:**
```bash
# Increase timeout in .env
N8N_TIMEOUT=120  # 2 minutes
```

## Summary vs Detailed Backlinks

| Feature | Summary API | Detailed Backlinks |
|---------|------------|-------------------|
| **Called in** | `_collect_essential_data()` | `_collect_detailed_data()` |
| **Purpose** | Get totals/metrics | Get individual records |
| **N8N Used** | ✅ Yes | ✅ Yes |
| **Backend Method** | `trigger_backlinks_summary_workflow()` | `trigger_backlinks_workflow()` |
| **Webhook URL** | `N8N_WEBHOOK_URL_SUMMARY` | `N8N_WEBHOOK_URL` |
| **Callback Endpoint** | `/api/v1/n8n/webhook/backlinks-summary` | `/api/v1/n8n/webhook/backlinks` |
| **Data Structure** | `{backlinks, referring_domains, rank}` | `{items: [...], total_count: N}` |
| **Fallback** | Direct DataForSEO API (will fail if disabled) | Direct DataForSEO API (will fail if disabled) |

## Next Steps

1. ✅ Configure `backend/.env` with both N8N webhook URLs
2. ✅ Create two N8N workflows (summary and detailed)
3. ✅ Verify both workflows are active
4. ✅ Start ngrok and update `N8N_CALLBACK_URL`
5. ✅ Restart backend server
6. ✅ Test from frontend
