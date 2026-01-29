# Step-by-Step: Add Volume Mount to n8n in Coolify

## Step 1: Find the Compose File Location

Run this command to find where the compose file is:

```bash
docker inspect n8n-ugogs4kook4s804wgsssogoc | grep -i compose
```

Or check the container's labels:

```bash
docker inspect n8n-ugogs4kook4s804wgsssogoc | grep -A 5 "Labels"
```

## Step 2: Search for Compose Files

```bash
# Search in common Coolify locations
find /data -name "docker-compose.yml" 2>/dev/null
find /data -name "compose.yml" 2>/dev/null

# Or check Coolify application directories
ls -la /data/coolify/applications/ 2>/dev/null
ls -la /data/applications/ 2>/dev/null
```

## Step 3: Edit the Compose File

Once you find it, navigate and edit:

```bash
cd /path/to/application/directory
sudo nano docker-compose.yml
```

## Step 4: Add Volume Mount

Find the `n8n` service section and add to `volumes:`:

```yaml
services:
  n8n-ugogs4kook4s804wgsssogoc:  # or just 'n8n'
    # ... existing config ...
    volumes:
      # Keep existing volumes
      - n8n-data:/home/node/.n8n
      - ugogs4kook4s804wgsssogoc_n8n-data:/home/node/.n8n
      
      # ADD THIS LINE (replace with your actual VPS path)
      - /var/www/auction-files:/app/auction-files
```

## Step 5: Save and Restart

- Save: `Ctrl+X`, then `Y`, then `Enter`
- Restart in Coolify UI or run: `docker-compose restart`








