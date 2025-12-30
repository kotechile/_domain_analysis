# Fix "File Not Writable" Error in n8n

## Problem
Even though permissions look correct, the WriteBinaryFile node still can't write files.

## Solutions

### Solution 1: Ensure Directory Exists Before Writing

Add a "Code" node before each "Save" node to ensure the directory exists:

```javascript
// Ensure directory exists
const fs = require('fs');
const path = require('path');

const filePath = '/app/auction-files/godaddy_tomorrow.json';
const dirPath = path.dirname(filePath);

// Create directory if it doesn't exist
if (!fs.existsSync(dirPath)) {
  fs.mkdirSync(dirPath, { recursive: true, mode: 0o755 });
}

// Return input unchanged
return $input.all();
```

### Solution 2: Check Parent Directory Permissions

The `/app` directory might not be writable. Check:

```bash
# In n8n terminal
ls -la /app
ls -la /app/auction-files
```

If `/app` is owned by root, that could be the issue.

### Solution 3: Use Different Path

Try using a path within the existing mounted volume:

```javascript
// Use /home/node/.n8n/auction-files instead
const filePath = '/home/node/.n8n/auction-files/godaddy_tomorrow.json';
```

This path is already writable since it's in the mounted n8n data volume.

### Solution 4: Check WriteBinaryFile Node Options

In the WriteBinaryFile node, check if there are any options that need to be set:
- "Create directory if it doesn't exist" (if available)
- File permissions options

### Solution 5: Verify Container User

Make sure the workflow runs as the node user:

```bash
# Check what user the workflow runs as
# In n8n terminal
whoami
id
```

The workflow should run as `node` (UID 1000).





