# Using docker-compose.override.yml in Coolify

## Problem

Coolify automatically regenerates `docker-compose.yml` from its internal configuration, so manual edits get overwritten on restart.

## Solution: Use docker-compose.override.yml

Docker Compose automatically merges `docker-compose.override.yml` with the main compose file. Coolify won't overwrite this file.

## Steps

### 1. Navigate to the Service Directory

```bash
cd /data/coolify/services/ugogs4kook4s804wgsssogoc
```

### 2. Create docker-compose.override.yml

```bash
sudo nano docker-compose.override.yml
```

### 3. Add Your Volume Mount

Paste this content:

```yaml
version: '3.8'

services:
  n8n:
    volumes:
      - /var/www/auction-files:/app/auction-files
```

**Important**: 
- The service name must match exactly (`n8n` in this case)
- Only include what you want to add/override
- The volumes list will be merged with the existing volumes

### 4. Save and Exit

- Press `Ctrl+O` to save
- Press `Enter` to confirm
- Press `Ctrl+X` to exit

### 5. Restart the Service

**Option A: Via Coolify UI**
- Go to your n8n service in Coolify
- Click "Restart" or "Redeploy"

**Option B: Via Command Line**
```bash
cd /data/coolify/services/ugogs4kook4s804wgsssogoc
docker-compose down
docker-compose up -d
```

### 6. Verify It Works

```bash
# In Coolify Terminal tab
ls -la /app/auction-files

# Test write
touch /app/auction-files/test.txt

# Check on VPS
ls -la /var/www/auction-files/
```

## How It Works

Docker Compose automatically:
1. Reads `docker-compose.yml` (managed by Coolify)
2. Reads `docker-compose.override.yml` (your custom config)
3. Merges them together
4. Uses the merged configuration

Your override file persists even when Coolify regenerates the main compose file!

## File Structure

```
/data/coolify/services/ugogs4kook4s804wgsssogoc/
├── docker-compose.yml          # Managed by Coolify (don't edit)
├── docker-compose.override.yml # Your custom config (safe to edit)
└── .env                        # Environment variables
```

## Troubleshooting

### Volume Not Mounting

1. Check file exists: `ls -la docker-compose.override.yml`
2. Check syntax: `docker-compose config` (validates the merged config)
3. Verify service name matches: Must be `n8n` (check main compose file)

### Still Getting Overwritten

- Make sure you're editing `docker-compose.override.yml`, NOT `docker-compose.yml`
- The override file should be in the same directory as the main compose file

### Check Merged Configuration

To see the final merged configuration:

```bash
cd /data/coolify/services/ugogs4kook4s804wgsssogoc
docker-compose config
```

This shows you exactly what Docker Compose will use, including your overrides.





