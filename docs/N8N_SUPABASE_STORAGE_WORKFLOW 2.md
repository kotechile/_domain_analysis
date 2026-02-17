# N8N Workflow: Upload to Supabase Storage

## Overview

This workflow uploads auction files to Supabase Storage and then triggers the backend to process them.

## Setup Instructions

### 1. Get Supabase Service Role Key

1. Go to your Supabase project: https://sbdomain.giniloh.com
2. Navigate to **Settings** → **API**
3. Copy the **Service Role Key** (not the anon key - you need service role for storage uploads)

### 2. Create Header Auth Credential in n8n

1. Go to n8n → **Credentials** → **New**
2. Select **Header Auth** credential type
3. Name it: `sbdomainservice`
4. Configure:
   - **Header Name**: `Authorization`
   - **Value**: Your Supabase service role key (the full JWT token)
   - **Header Prefix**: `Bearer ` (with space after Bearer)
5. Save the credential

**Note:** The workflow uses this credential for the `Authorization` header. You'll also need to create a Generic Credential Type for the `apikey` header (see below).

### 2.1 Create Generic Credential Type for Service Role Key (Alternative)

If environment variables aren't accessible, create a Generic Credential Type:

1. Go to n8n → **Credentials** → **New**
2. Select **Generic Credential Type**
3. Name it: `supabase-service-role-key`
4. Add a field:
   - **Field Name**: `serviceRoleKey`
   - **Field Type**: Text (secret)
   - **Value**: Your Supabase service role key
5. Save the credential

**Note:** You'll need to reference this credential in a Code node to extract the value (see troubleshooting below).

### 3. Configure Environment Variables in Coolify

The workflow uses environment variables for backend URL. Set this in Coolify for your n8n service:

**Required Environment Variables:**
- `BACKEND_API_URL` - Your ngrok URL or production backend URL (already set ✅)

**Optional (if env var access works after restart):**
- `SUPABASE_SERVICE_ROLE_KEY` - Your Supabase service role key (used for `apikey` header)
- `SUPABASE_URL` - Your Supabase URL (hardcoded in workflow, but can use env var if accessible)

**Note:** Make sure `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` (already set ✅). **Restart n8n service** after changing this setting.

The workflow uses:
- Header Auth credential (`sbdomainservice`) for `Authorization: Bearer` header
- Hardcoded Supabase URL: `https://sbdomain.giniloh.com`
- `{{ $env.SUPABASE_SERVICE_ROLE_KEY }}` for `apikey` header (if env vars are accessible)
- `{{ $env.BACKEND_API_URL }}` for backend processing triggers

### 4. Verify Bucket Exists

Make sure the `listingfiles` bucket exists in Supabase:
1. Go to **Storage** → **Buckets**
2. Check if `listingfiles` bucket exists
3. If not, create it with:
   - Public: false (or true if you want public access)
   - File size limit: 200MB (or as needed)
   - Allowed MIME types: `text/csv`, `application/json`, `application/zip`

### 5. Import Workflow

1. Import `Download and Process Auction Files - Supabase Storage.json` into n8n
2. When prompted, select the `sbdomainservice` credential for all upload nodes
3. Activate the workflow

## Workflow Flow

```
Schedule (6 AM)
  ↓
  ├─→ Download GoDaddy Tomorrow → Decompress → Prepare → Upload to Storage → Trigger Backend
  ├─→ Download GoDaddy Today → Decompress → Prepare → Upload to Storage → Trigger Backend
  ├─→ Download Namecheap Auctions → Prepare → Upload to Storage → Trigger Backend
  └─→ Download Namecheap Buy Now → Prepare → Upload to Storage → Trigger Backend
       ↓
    Aggregate Results
```

## How It Works

1. **Download**: Files are downloaded from GoDaddy/Namecheap
2. **Decompress**: ZIP files are extracted (GoDaddy only)
3. **Prepare**: Metadata is added (filename, auction_site, offering_type, bucket, path)
4. **Upload to Storage**: Files are uploaded to Supabase Storage bucket `listingfiles`
5. **Trigger Backend**: Backend endpoint `/api/v1/auctions/process-from-storage` is called with file location
6. **Backend Processing**: Backend downloads file from storage and processes it

## Backend Endpoint

The workflow calls:
```
POST /api/v1/auctions/process-from-storage
Body: {
  "bucket": "listingfiles",
  "path": "godaddy_tomorrow_2025-12-29T15-00-00.json",
  "auction_site": "godaddy",
  "offering_type": "auction",
  "filename": "godaddy_tomorrow_2025-12-29T15-00-00.json"
}
```

## Advantages

- ✅ No file size limits from HTTP uploads
- ✅ Files persist in Supabase Storage
- ✅ Backend can retry processing if needed
- ✅ No need to pass large files through ngrok
- ✅ More reliable than direct file uploads

## Troubleshooting

### Authorization Errors

- Verify service role key is correct
- Check bucket RLS policies allow service role to upload
- Ensure key is set in environment variables or workflow

### File Not Found in Storage

- Check bucket name is correct (`listingfiles`)
- Verify file was uploaded successfully (check Supabase Storage UI)
- Check file path is correct

### Backend Can't Download

- Verify backend has Supabase service role key configured
- Check bucket RLS policies allow service role to read
- Verify file path matches what was uploaded

### Environment Variables Not Accessible

If `{{ $env.SUPABASE_SERVICE_ROLE_KEY }}` is not working:

1. **Restart n8n service** after setting `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`
2. **Verify the env var is set** in Coolify
3. **Alternative**: Create a Generic Credential Type and use a Code node to extract the value:
   ```javascript
   // In a Code node before the upload nodes
   const credential = await $credentials.get('supabase-service-role-key');
   return [{
     json: {
       serviceRoleKey: credential.serviceRoleKey,
       // ... other data
     }
   }];
   ```
   Then reference `{{ $json.serviceRoleKey }}` in the `apikey` header.
4. **Temporary workaround**: Hardcode the service role key in the workflow (not recommended for production)

