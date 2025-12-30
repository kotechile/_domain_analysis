# Setting Up Volume Mount for n8n in Coolify

## Quick Setup Guide

### Step 1: Create Directory on VPS (if not already done)

SSH into your Hostinger VPS and create the directory:

```bash
# Choose a location (examples):
sudo mkdir -p /var/www/auction-files
# OR
sudo mkdir -p /home/your-username/auction-files
# OR
sudo mkdir -p /opt/auction-files

# Set permissions (n8n typically runs as user 1000)
sudo chown -R 1000:1000 /var/www/auction-files
sudo chmod 755 /var/www/auction-files
```

### Step 2: Add Volume Mount in Coolify

1. **Navigate to n8n service** in Coolify
2. Go to **Configuration** → **Persistent Storages** (you're already here)
3. Since volumes are read-only in the UI, you need to edit the Docker Compose file:
   - Click **"Advanced"** dropdown
   - Select **"Edit Docker Compose"** or **"Edit Compose File"**
   - This opens the compose file editor

4. **Add the volume mount** to the n8n service:

```yaml
services:
  n8n:
    # ... existing configuration ...
    volumes:
      # Keep existing volumes
      - n8n-data:/home/node/.n8n
      - ugogs4kook4s804wgsssogoc_n8n-data:/home/node/.n8n
      
      # ADD THIS LINE - Replace with your actual VPS path
      - /var/www/auction-files:/app/auction-files
```

**Important**: 
- Replace `/var/www/auction-files` with the actual path on your VPS
- The path after the colon (`/app/auction-files`) is the path inside the container that n8n will see

### Step 3: Save and Redeploy

1. Click **"Save"** or **"Update"** in the compose file editor
2. Click **"Redeploy"** or **"Restart"** button
3. Wait for the container to restart

### Step 4: Verify the Mount

1. Go to **"Terminal"** tab in Coolify
2. Run: `ls -la /app/auction-files`
3. You should see your VPS directory contents

### Step 5: Update Workflow Paths

Update your n8n workflow to use `/app/auction-files/` instead of `/tmp/auction-files/`:

- All "Save" nodes: Change `fileName` from `/tmp/auction-files/...` to `/app/auction-files/...`
- All "Prepare" nodes: Change `file_path` in the JavaScript code

## Recommended Container Paths

Common choices for the container path (right side of the mount):

- `/app/auction-files` - Recommended (clean, application-specific)
- `/home/node/auction-files` - If you want it in n8n's home directory
- `/data/auction-files` - If you prefer a data directory
- `/tmp/auction-files` - Works but `/tmp` may be cleared on container restart (not recommended)

**Recommendation**: Use `/app/auction-files` as it's clear and persistent.

## Example Complete Volume Mount

If your VPS directory is at `/var/www/auction-files`, the mount would be:

```yaml
volumes:
  - /var/www/auction-files:/app/auction-files
```

This means:
- **Host path**: `/var/www/auction-files` (on your VPS)
- **Container path**: `/app/auction-files` (inside n8n container)
- Files written to `/app/auction-files/` in n8n will appear in `/var/www/auction-files/` on your VPS

## Troubleshooting

### Permission Issues

If n8n can't write files:

```bash
# On VPS, check current ownership
ls -la /var/www/auction-files

# Find n8n container's user ID
docker exec <n8n-container> id

# Set ownership (usually UID 1000)
sudo chown -R 1000:1000 /var/www/auction-files
sudo chmod 755 /var/www/auction-files
```

### Directory Not Found

1. Verify the host path exists: `ls -la /var/www/auction-files`
2. Check the compose file syntax (no typos in paths)
3. Restart the container after adding the mount

### Files Not Appearing on VPS

1. Verify you're checking the correct host path
2. Check container logs for errors
3. Test write from container: `docker exec <n8n-container> touch /app/auction-files/test.txt`
4. Check if file appears on host: `ls -la /var/www/auction-files/`

