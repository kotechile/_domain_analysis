# N8N Scheduled Auction File Download Workflow

## Overview

This workflow automatically downloads auction files from GoDaddy and Namecheap daily at 6:00 AM, saves them to a temporary folder, and triggers the backend API to process them.

## Workflow Features

- **Scheduled Execution**: Runs daily at 6:00 AM (configurable via cron expression)
- **Parallel Downloads**: Downloads all 4 files simultaneously for efficiency
- **File Management**: Saves files to `/tmp/auction-files/` (overwrites previous files)
- **Automatic Processing**: Automatically uploads files to backend API after download
- **Error Handling**: Aggregates results and reports success/failure for each file

## Files Processed

1. **GoDaddy - Tomorrow**: `all_listings_ending_tomorrow.json.zip`
   - Extracts ZIP file
   - Saves as `godaddy_tomorrow.json`
   - Uploads via `/api/v1/auctions/upload-json`

2. **GoDaddy - Today**: `all_listings_ending_today.json.zip`
   - Extracts ZIP file
   - Saves as `godaddy_today.json`
   - Uploads via `/api/v1/auctions/upload-json`

3. **Namecheap Auctions**: `Namecheap_Market_Sales.csv`
   - Saves directly as CSV
   - Uploads via `/api/v1/auctions/upload-csv`

4. **Namecheap Buy Now**: `Namecheap_Market_Sales_Buy_Now.csv`
   - Saves directly as CSV
   - Uploads via `/api/v1/auctions/upload-csv`

## Setup Instructions

### 1. Import Workflow

1. Open your N8N instance
2. Click "Import from File" or "Import from URL"
3. Select the file: `Download and Process Auction Files - Scheduled.json`
4. The workflow will be imported with all nodes configured

### 2. Configure Environment Variable

Set the `BACKEND_API_URL` environment variable in your N8N instance:

- **Option A**: Set in N8N environment variables
  - Go to Settings → Environment Variables
  - Add: `BACKEND_API_URL=http://localhost:8000` (or your backend URL)

- **Option B**: Set in workflow execution environment
  - The workflow will default to `http://localhost:8000` if not set

### 3. Create Directory on VPS and Mount to n8n

**On your Hostinger VPS** (via SSH), create the directory:

```bash
# Create directory (choose your preferred location)
sudo mkdir -p /var/www/auction-files
# OR
sudo mkdir -p /home/your-username/auction-files

# Set permissions (n8n runs as user 1000)
sudo chown -R 1000:1000 /var/www/auction-files
sudo chmod 755 /var/www/auction-files
```

**In Coolify**, add a volume mount to n8n:

1. Go to n8n service → **Configuration** → **Advanced** → **Edit Docker Compose**
2. Add this volume mount to the n8n service:
   ```yaml
   volumes:
     # ... existing volumes ...
     - /var/www/auction-files:/app/auction-files
   ```
   (Replace `/var/www/auction-files` with your actual VPS path)
3. Save and redeploy the service

See `docs/COOLIFY_N8N_VOLUME_SETUP.md` for detailed instructions.

### 4. Configure Schedule (Optional)

To change the schedule time, edit the "Daily Schedule (6 AM)" node:

- Current: `0 6 * * *` (6:00 AM daily)
- Format: Cron expression (minute hour day month weekday)
- Examples:
  - `0 5 * * *` - 5:00 AM daily
  - `0 7 * * 1-5` - 7:00 AM on weekdays only
  - `0 */6 * * *` - Every 6 hours

### 5. Activate Workflow

1. Click the "Active" toggle in the top right of the workflow
2. The workflow will now run automatically at the scheduled time

## Workflow Structure

```
Schedule Trigger (6 AM)
  ↓
  ├─→ Download GoDaddy Tomorrow → Extract ZIP → Save → Prepare → Upload
  ├─→ Download GoDaddy Today → Extract ZIP → Save → Prepare → Upload
  ├─→ Download Namecheap Auctions → Save → Prepare → Upload
  └─→ Download Namecheap Buy Now → Save → Prepare → Upload
       ↓
    Aggregate Results
```

## Backend API Endpoints Used

- **JSON Upload**: `POST /api/v1/auctions/upload-json`
  - Query params: `auction_site=godaddy`, `offering_type=auction`
  - Body: multipart/form-data with `file` field

- **CSV Upload**: `POST /api/v1/auctions/upload-csv`
  - Query params: `auction_site=namecheap`, `offering_type=auction|buy_now`
  - Body: multipart/form-data with `file` field

## Response Format

The backend returns:
```json
{
  "success": true,
  "job_id": "uuid-string",
  "message": "CSV upload started. Use /auctions/upload-progress/{job_id} to check progress.",
  "filename": "filename.ext",
  "auction_site": "godaddy"
}
```

## Monitoring

### Check Workflow Execution

1. Go to "Executions" in N8N
2. Filter by workflow name
3. View execution details and logs

### Check Backend Processing

1. Use the `job_id` from the upload response
2. Check progress: `GET /api/v1/auctions/upload-progress/{job_id}`
3. Monitor backend logs for processing status

### Aggregate Results

The final "Aggregate Results" node provides:
```json
{
  "summary": {
    "total_files": 4,
    "successful": 3,
    "failed": 1
  },
  "results": [
    {
      "source": "godaddy_tomorrow",
      "success": true,
      "job_id": "uuid",
      "message": "...",
      "filename": "godaddy_tomorrow.json",
      "auction_site": "godaddy"
    },
    ...
  ],
  "timestamp": "2025-01-31T06:00:00.000Z"
}
```

## Troubleshooting

### Files Not Downloading

- Check internet connectivity from N8N server
- Verify URLs are still valid
- Check N8N execution logs for HTTP errors

### ZIP Extraction Failing

- Ensure `extractFromFile` node is properly configured
- Check that downloaded file is actually a ZIP
- Verify file permissions on `/tmp/auction-files/`

### Backend Upload Failing

- Verify `BACKEND_API_URL` is correct
- Check backend server is running
- Verify backend API endpoints are accessible
- Check backend logs for errors

### Files Not Saving

- Verify `/tmp/auction-files/` directory exists
- Check write permissions on the directory
- Ensure sufficient disk space

## Manual Execution

You can manually trigger the workflow:

1. Click "Execute Workflow" button
2. The workflow will run immediately (not waiting for schedule)
3. Useful for testing or immediate processing

## Customization

### Change File Paths

The workflow uses `/app/auction-files/` as the container path. To change:

1. Update all "Save" nodes: Change `fileName` from `/app/auction-files/...` to your desired path
2. Update all "Prepare" nodes: Change `file_path` in the JavaScript code
3. Update the volume mount in Docker Compose to match your new container path

**Note**: The container path (right side of volume mount) must match the paths in the workflow.

### Add More Sources

1. Add new HTTP Request node for download
2. Add Save node if needed
3. Add Prepare node with metadata
4. Add Upload node with correct endpoint
5. Connect to Aggregate Results node

### Error Notifications

Add notification nodes after "Aggregate Results":
- Email node for failures
- Slack/Discord webhook for alerts
- SMS notifications for critical errors

## Notes

- Files are overwritten each day (previous day's files are replaced)
- The workflow processes files in parallel for speed
- Backend processes files asynchronously (returns job_id immediately)
- Use job_id to track processing progress via backend API

