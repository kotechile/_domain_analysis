# Fix N8N Summary Webhook

## Issue

The Summary webhook is returning 404:
```
"The requested webhook \"POST webhook/backlinks-summary\" is not registered."
```

## Solution

### Option 1: Fix the Webhook Path (Recommended)

1. **Open the "DataForSEO Backlinks Summary" workflow** in N8N
2. **Click on the Webhook node** (first node)
3. **Check the Path field**:
   - Current path might be: `/backlinks-summary` or `/webhook/backlinks-summary`
   - **Should be**: `/webhook/backlinks-summary` (to match the URL pattern)
4. **Update the Path** to: `/webhook/backlinks-summary`
5. **Save the workflow** (Ctrl+S or Cmd+S)
6. **Make sure workflow is Active** (green toggle should be ON)
7. **Wait a few seconds** for N8N to register the webhook

### Option 2: Update Backend Config to Match N8N

If you prefer to keep the N8N path as-is, update your backend `.env`:

```bash
# If N8N webhook path is just "/backlinks-summary" (without /webhook/)
N8N_WEBHOOK_URL_SUMMARY=https://n8n.aichieve.net/webhook/backlinks-summary
```

## Verification

After fixing, test again:

```bash
curl -X POST https://n8n.aichieve.net/webhook/webhook/backlinks-summary \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "test.com",
    "callback_url": "https://httpbin.org/post",
    "request_id": "test-summary",
    "type": "summary"
  }'
```

**Expected**: Should return HTTP 200 (not 404)

## N8N Webhook Path Pattern

N8N webhook URLs follow this pattern:
```
https://n8n.aichieve.net/webhook/{WORKFLOW_PATH}
```

Where `{WORKFLOW_PATH}` is the **Path** you set in the Webhook node.

**Common patterns:**
- Path: `/backlinks-summary` → URL: `https://n8n.aichieve.net/webhook/backlinks-summary`
- Path: `/webhook/backlinks-summary` → URL: `https://n8n.aichieve.net/webhook/webhook/backlinks-summary`

**Your Details workflow uses**: `/webhook/backlinks-details` (that's why it works)

**Your Summary workflow should use**: `/webhook/backlinks-summary` (to match the pattern)

## Quick Fix Steps

1. Open "DataForSEO Backlinks Summary" workflow
2. Click Webhook node
3. Set Path to: `/webhook/backlinks-summary`
4. Save workflow (Ctrl+S / Cmd+S)
5. Verify Active toggle is ON
6. Test with curl command above

















