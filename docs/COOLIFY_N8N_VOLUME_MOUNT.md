# Mounting Host Directory to n8n in Coolify

## Overview

To make a directory on your Hostinger VPS accessible to n8n running in Docker via Coolify, you need to add a volume mount to the n8n service's Docker Compose configuration.

## Step-by-Step Instructions

### 1. Access Docker Compose File in Coolify

1. Go to your n8n service in Coolify
2. Click on **"Advanced"** dropdown menu
3. Select **"Edit Docker Compose"** or **"Edit Compose File"**
4. This will show you the Docker Compose configuration for n8n

### 2. Add Volume Mount

In the n8n service section, add a `volumes` section (or add to existing volumes). The format should be:

```yaml
services:
  n8n:
    # ... existing configuration ...
    volumes:
      # Existing volumes (keep these)
      - n8n-data:/home/node/.n8n
      - ugogs4kook4s804wgsssogoc_n8n-data:/home/node/.n8n
      
      # Add this new volume mount for auction files
      - /path/on/host/vps:/app/auction-files
```

**Important**: Replace `/path/on/host/vps` with the actual path on your Hostinger VPS where you created the directory.

### 3. Example Configuration

If you created the directory at `/home/username/auction-files` on your VPS, the volume mount would be:

```yaml
volumes:
  - /home/username/auction-files:/app/auction-files
```

Or if you prefer a more standard location:

```yaml
volumes:
  - /var/www/auction-files:/app/auction-files
```

### 4. Container Path

The path inside the container (`/app/auction-files` in the example) is what n8n will see. You can choose any path, but common choices are:
- `/app/auction-files`
- `/tmp/auction-files`
- `/data/auction-files`
- `/home/node/auction-files`

### 5. Save and Redeploy

1. Save the Docker Compose file in Coolify
2. Click **"Redeploy"** or **"Restart"** to apply changes
3. The volume mount will be active after the container restarts

### 6. Verify Mount

You can verify the mount is working by:

1. Go to **"Terminal"** tab in Coolify
2. Run: `ls -la /app/auction-files` (or whatever path you chose)
3. You should see the directory contents from your VPS

## Directory Permissions

Make sure the directory on your VPS has proper permissions:

```bash
# On your Hostinger VPS (via SSH)
sudo mkdir -p /path/to/auction-files
sudo chown -R 1000:1000 /path/to/auction-files  # n8n runs as user 1000
sudo chmod 755 /path/to/auction-files
```

Or if you know the exact user ID n8n runs as:

```bash
# Check n8n container user
docker exec <n8n-container-name> id

# Then set ownership accordingly
sudo chown -R <uid>:<gid> /path/to/auction-files
```

## Update Workflow Paths

After mounting, update your n8n workflow to use the mounted directory path instead of `/tmp/auction-files/`.

The workflow file paths should be updated to match your container mount path (e.g., `/app/auction-files/`).

## Troubleshooting

### Permission Denied Errors

If n8n can't write to the directory:
1. Check directory ownership: `ls -la /path/to/auction-files`
2. Ensure n8n user (usually UID 1000) owns the directory
3. Check directory permissions: should be 755 or 775

### Directory Not Visible

1. Verify the volume mount in Docker Compose
2. Check that the host path exists
3. Restart the n8n container
4. Check container logs for mount errors

### Files Not Persisting

- Ensure you're using a bind mount (host path) not a named volume
- Verify the host path is correct and accessible
- Check that files are being written to the correct path inside the container





