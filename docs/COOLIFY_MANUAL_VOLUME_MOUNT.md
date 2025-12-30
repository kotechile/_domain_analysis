# Manual Volume Mount for Coolify Services

If `docker-compose.override.yml` isn't being picked up by Coolify, we need to add the volume mount directly to the container.

## Method: Add Volume to Running Container

Since containers can't have volumes added after creation, we need to recreate it with the volume.

### Step 1: Get Current Container Configuration

```bash
# Get the full docker run command that created the container
docker inspect n8n-ugogs4kook4s804wgsssogoc --format='{{json .Config}}' | jq .

# Or get the mount points
docker inspect n8n-ugogs4kook4s804wgsssogoc | grep -A 20 Mounts
```

### Step 2: Stop and Remove Container

```bash
docker stop n8n-ugogs4kook4s804wgsssogoc
docker rm n8n-ugogs4kook4s804wgsssogoc
```

### Step 3: Recreate with Volume Mount

We need to use the same command Coolify uses, but add our volume. However, since Coolify manages this, the better approach is to modify the compose file that Coolify uses, or find where Coolify stores the service configuration.

## Alternative: Check Coolify's Service Configuration

Coolify might store service configurations in a database or config file. Let's check:

```bash
# Look for Coolify's database or config
find /data/coolify -name "*.db" -o -name "*.sqlite" 2>/dev/null
find /data/coolify -type f -name "*config*" 2>/dev/null | grep -i n8n
```

## Best Solution: Use Coolify's UI or API

Since Coolify manages everything, the best approach is to find the proper way to add volumes through Coolify's interface or configuration system.





