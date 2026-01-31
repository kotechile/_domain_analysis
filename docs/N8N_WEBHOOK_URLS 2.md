# N8N Webhook URLs - Current Configuration

## Actual Webhook URLs

Based on your N8N setup:

1. **Summary Backlinks**: 
   - URL: `https://n8n.aichieve.net/webhook/webhook/backlinks`
   - Path in N8N: `/webhook/backlinks`

2. **Detailed Backlinks**: 
   - URL: `https://n8n.aichieve.net/webhook/webhook/backlinks-details`
   - Path in N8N: `/webhook/backlinks-details`

## Backend Configuration

Update your `backend/.env` file with:

```bash
# N8N Integration Settings
N8N_ENABLED=true

# Summary Backlinks Workflow
N8N_WEBHOOK_URL_SUMMARY=https://n8n.aichieve.net/webhook/webhook/backlinks

# Detailed Backlinks Workflow
N8N_WEBHOOK_URL=https://n8n.aichieve.net/webhook/webhook/backlinks-details

# Callback URL (use your ngrok URL)
N8N_CALLBACK_URL=https://YOUR-NGROK-URL.ngrok-free.dev/api/v1/n8n/webhook/backlinks
N8N_TIMEOUT=60
N8N_USE_FOR_BACKLINKS=true
N8N_USE_FOR_SUMMARY=true
```

## Testing

### Test Summary Webhook

```bash
curl -X POST https://n8n.aichieve.net/webhook/webhook/backlinks \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "test.com",
    "callback_url": "https://httpbin.org/post",
    "request_id": "test-summary",
    "type": "summary"
  }'
```

### Test Details Webhook

```bash
curl -X POST https://n8n.aichieve.net/webhook/webhook/backlinks-details \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "test.com",
    "limit": 100,
    "callback_url": "https://httpbin.org/post",
    "request_id": "test-details",
    "type": "detailed"
  }'
```

## Important Notes

- Both workflows use the same base path pattern: `/webhook/webhook/...`
- Summary uses `/backlinks` (shorter path)
- Details uses `/backlinks-details` (more specific)
- Make sure both workflows are **Active** in N8N
- Both webhooks should return HTTP 200 when tested



























