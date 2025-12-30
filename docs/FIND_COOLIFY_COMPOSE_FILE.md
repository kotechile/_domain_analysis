# Finding Your n8n Docker Compose File in Coolify

## Quick Commands

Run these on your VPS (via SSH) to locate the compose file:

### Option 1: Search by Container Name

```bash
# Find the n8n container
docker ps -a | grep n8n

# Get the container's compose file location
docker inspect <container-name-or-id> | grep -i compose
```

### Option 2: Search Common Coolify Directories

```bash
# Search in common Coolify locations
find /data -name "docker-compose.yml" 2>/dev/null | grep -i n8n

# Or search all of /data
find /data -name "*compose*" -type f 2>/dev/null
```

### Option 3: Check Coolify Application Directories

```bash
# List all applications
ls -la /data/coolify/applications/ 2>/dev/null
# OR
ls -la /data/applications/ 2>/dev/null

# Then check each directory
cd /data/coolify/applications/
for dir in */; do
  echo "=== $dir ==="
  ls -la "$dir" | grep -i compose
done
```

### Option 4: Find by Project Name

```bash
# If you know your project name (e.g., "production")
find /data -type d -name "*production*" 2>/dev/null
find /data -type d -name "*n8n*" 2>/dev/null
```

## Once You Find It

1. Navigate to the directory:
   ```bash
   cd /path/to/application/directory
   ```

2. Edit the compose file:
   ```bash
   sudo nano docker-compose.yml
   ```

3. Add the volume mount (see other guides for exact syntax)

4. Restart the service in Coolify UI or run:
   ```bash
   docker-compose restart
   ```





