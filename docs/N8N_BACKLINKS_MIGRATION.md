# N8N Backlinks Migration Summary

## Overview

The backend has been updated to **require N8N for all backlinks operations**. Direct HTTP calls to DataForSEO API are no longer allowed as a fallback, which is necessary for subscriptions that don't allow HTTP access.

## Changes Made

### 1. Backend Code Updates

**File**: `backend/src/services/analysis_service.py`

#### Dual/Async Mode (Primary Path)
- **Before**: Used N8N if enabled, fell back to direct HTTP if N8N failed
- **After**: **Requires N8N** - raises exception if N8N is not enabled or fails
- **Location**: `_collect_detailed_data()` method, lines ~287-343

#### Legacy Mode (Fallback Path)
- **Before**: Used direct HTTP calls via `get_detailed_backlinks()`
- **After**: **Requires N8N** - uses N8N workflow even in legacy mode
- **Location**: `_collect_detailed_data()` method, lines ~457-470

### 2. Error Handling

The backend now raises clear exceptions when:
- N8N is not enabled (`N8N_ENABLED=false` or `N8N_USE_FOR_BACKLINKS=false`)
- N8N workflow trigger fails
- N8N workflow times out (120 seconds)
- No data received from N8N workflow

### 3. Documentation

**New File**: `docs/N8N_BACKLINKS_WORKFLOW.md`
- Complete step-by-step workflow setup guide
- Import-ready JSON workflow
- Troubleshooting guide
- Best practices

## Required Configuration

Ensure your `backend/.env` file has:

```bash
# N8N Integration Settings (REQUIRED)
N8N_ENABLED=true
N8N_WEBHOOK_URL=https://n8n.aichieve.net/webhook/webhook/backlinks-details
N8N_CALLBACK_URL=https://your-backend.com/api/v1/n8n/webhook/backlinks
N8N_TIMEOUT=120
N8N_USE_FOR_BACKLINKS=true  # REQUIRED - no HTTP fallback
```

## Migration Steps

### 1. Set Up N8N Workflow

Follow the guide in `docs/N8N_BACKLINKS_WORKFLOW.md` to:
- Create the workflow in N8N
- Configure DataForSEO node
- Set up error handling
- Test the workflow

### 2. Update Backend Configuration

1. Set `N8N_ENABLED=true` in `.env`
2. Set `N8N_USE_FOR_BACKLINKS=true` in `.env`
3. Configure `N8N_WEBHOOK_URL` with your workflow URL
4. Configure `N8N_CALLBACK_URL` with your backend webhook endpoint

### 3. Test the Integration

1. Start your backend server
2. Trigger a domain analysis from the frontend
3. Check N8N execution logs
4. Verify data is received in backend webhook endpoint
5. Confirm analysis completes successfully

## Breaking Changes

### ⚠️ Important: No HTTP Fallback

**Before**: If N8N failed, the system would fall back to direct HTTP calls
**After**: If N8N fails, the analysis will fail with a clear error message

### Error Messages

You may see these new error messages:

1. **"N8N is required for backlinks analysis. Please enable N8N in your configuration."**
   - **Solution**: Set `N8N_ENABLED=true` and `N8N_USE_FOR_BACKLINKS=true` in `.env`

2. **"Failed to trigger N8N workflow for backlinks. Please check N8N configuration and workflow status."**
   - **Solution**: 
     - Verify `N8N_WEBHOOK_URL` is correct
     - Check N8N workflow is active
     - Verify N8N is accessible

3. **"N8N workflow did not return backlinks data within 120 seconds"**
   - **Solution**:
     - Check N8N execution logs for errors
     - Verify callback URL is accessible
     - Check DataForSEO credentials
     - Reduce limit if needed

## Benefits

1. **Subscription Compliance**: Works with subscriptions that don't allow HTTP access
2. **Consistent Architecture**: All backlinks go through N8N
3. **Better Error Handling**: Clear error messages when N8N fails
4. **Cost Control**: N8N can implement rate limiting and cost monitoring
5. **Flexibility**: Easy to modify workflow logic in N8N without code changes

## Rollback (If Needed)

If you need to temporarily allow HTTP fallback (not recommended for restricted subscriptions):

1. Modify `backend/src/services/analysis_service.py`
2. In `_collect_detailed_data()`, change the check from:
   ```python
   if not use_n8n:
       raise Exception("N8N is required...")
   ```
   To:
   ```python
   if not use_n8n:
       # Fallback to HTTP (only if subscription allows)
       backlinks_data = await self.dataforseo_service.get_detailed_backlinks(domain, 10000)
   ```

**Note**: This will only work if your DataForSEO subscription allows HTTP access.

## Support

For issues:
1. Check `docs/N8N_BACKLINKS_WORKFLOW.md` troubleshooting section
2. Review N8N execution logs
3. Check backend logs for error messages
4. Verify all configuration settings

## Next Steps

- ✅ Backend updated to require N8N
- ✅ Workflow documentation created
- ⏭️ Set up N8N workflow (follow `N8N_BACKLINKS_WORKFLOW.md`)
- ⏭️ Test integration
- ⏭️ Monitor for any issues


