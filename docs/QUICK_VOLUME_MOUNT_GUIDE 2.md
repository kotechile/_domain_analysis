# Quick Guide: Mount VPS Directory to n8n in Coolify

## What You Need

- **VPS Directory Path**: The path where you created the directory on Hostinger VPS
  - Example: `/var/www/auction-files` or `/home/username/auction-files`
- **Container Path**: `/app/auction-files` (already configured in workflow)

## Steps

### 1. Set Permissions on VPS (via SSH)

```bash
# Replace with your actual path
sudo chown -R 1000:1000 /var/www/auction-files
sudo chmod 755 /var/www/auction-files
```

### 2. Add Volume Mount in Coolify

1. In Coolify, go to your **n8n service**
2. Click **"Advanced"** dropdown → **"Edit Docker Compose"**
3. Find the `n8n` service section
4. Add this line to the `volumes:` section:

```yaml
volumes:
  # ... existing volumes (keep them) ...
  - /var/www/auction-files:/app/auction-files
```

**Replace `/var/www/auction-files` with your actual VPS path!**

5. Click **"Save"** or **"Update"**
6. Click **"Redeploy"** or **"Restart"**

### 3. Verify It Works

1. Go to **"Terminal"** tab in Coolify
2. Run: `ls -la /app/auction-files`
3. You should see your VPS directory

### 4. Test Write Access

In the Terminal, run:
```bash
touch /app/auction-files/test.txt
ls -la /app/auction-files/
```

Then check on your VPS:
```bash
ls -la /var/www/auction-files/
```

You should see `test.txt` in both places!

## Example Docker Compose Section

Your n8n service should look like this:

```yaml
services:
  n8n:
    image: n8nio/n8n:latest
    # ... other config ...
    volumes:
      - n8n-data:/home/node/.n8n
      - ugogs4kook4s804wgsssogoc_n8n-data:/home/node/.n8n
      - /var/www/auction-files:/app/auction-files  # <-- ADD THIS LINE
```

## Workflow is Already Updated

The workflow file has been updated to use `/app/auction-files/` - no changes needed there!

## Troubleshooting

**Can't write files?**
- Check ownership: `sudo chown -R 1000:1000 /var/www/auction-files`
- Check permissions: `sudo chmod 755 /var/www/auction-files`

**Directory not visible?**
- Verify the path in Docker Compose matches your VPS path
- Restart the container after adding the mount
- Check container logs for errors

**Files not appearing on VPS?**
- Verify you're checking the correct host path
- Test with: `docker exec <n8n-container> touch /app/auction-files/test.txt`








