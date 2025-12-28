# Large File Upload Improvements

## Issue
Large CSV files (800K+ records) were failing with 500 errors during upload.

## Root Causes
1. **Memory Issues**: Entire file was being read into memory at once
2. **Timeout Issues**: Supabase storage uploads timing out for large files
3. **No Retry Logic**: Single attempt failures caused complete upload failure
4. **Poor Error Messages**: Generic 500 errors didn't help diagnose the issue

## Improvements Made

### 1. Chunked File Reading
- Files are now read in 1MB chunks instead of loading entire file at once
- Reduces memory pressure during upload
- Better progress tracking

### 2. Retry Logic with Exponential Backoff
- 3 retry attempts for storage uploads
- Exponential backoff: 2s, 4s, 8s delays between retries
- Handles transient network issues

### 3. Enhanced Error Handling
- Specific error messages for different failure types:
  - Timeout errors
  - File size errors
  - Memory errors
- Better logging with file size information
- HTTP 413 for files that are too large

### 4. Improved Storage Upload
- Better error detection (timeout vs size vs other)
- File size logging (MB)
- Uses BytesIO for better memory management
- More descriptive error messages

### 5. N8N Trigger Resilience
- N8N workflow trigger failures no longer fail the entire upload
- File is saved to storage even if N8N trigger fails
- User can manually trigger processing if needed

## Code Changes

### `backend/src/api/routes/auctions.py`
- Chunked file reading (1MB chunks)
- Retry logic for storage uploads
- Enhanced error handling with specific messages
- File size warnings and limits

### `backend/src/services/database.py`
- Improved `upload_csv_to_storage()` method
- Better timeout and error detection
- Uses BytesIO for file handling
- More detailed logging

## Configuration

### Server Timeouts
- `timeout_keep_alive`: 1800 seconds (30 minutes) - Already configured in `run_server.py`
- This allows for very large file uploads

### File Size Limits
- Warning threshold: 500MB
- Files larger than 500MB will log a warning but still attempt upload

## Error Messages

Users will now see more helpful error messages:
- **Timeout**: "Upload timed out. The file may be too large. Please try again or split into smaller files."
- **Too Large**: "File is too large. Please split into smaller files."
- **Memory**: "Insufficient memory to process file. Please split into smaller files."
- **Storage Upload Failed**: "Failed to upload CSV to storage after 3 attempts: [error details]"

## Testing

To test large file uploads:
1. Upload a file > 100MB
2. Check backend logs for chunked reading progress
3. Verify retry logic if upload fails
4. Check that file appears in Supabase storage even if N8N trigger fails

## Future Improvements

1. **Streaming Upload**: If Supabase Python client supports it, stream directly to storage without loading into memory
2. **Progress Tracking**: Add progress endpoint to track upload status
3. **File Size Validation**: Reject files over a certain size before processing
4. **Background Processing**: Move file upload to background task queue

## Notes

- The Supabase Python client's `upload()` method requires the full file content, so we still need to load it into memory
- For extremely large files (>1GB), consider splitting files or using direct Supabase storage API
- N8N workflow processing happens asynchronously, so upload success doesn't guarantee immediate processing









