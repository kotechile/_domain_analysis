# Fix Write Permissions for n8n Workflow

## Problem
The workflow can't write files even though the directory exists and you can create files manually in the terminal.

## Solution: Fix Permissions

The n8n workflow runs as the `node` user (UID 1000). We need to ensure the directory has the correct permissions.

### Step 1: Check Current Permissions

In the n8n terminal (Coolify Terminal tab):

```bash
ls -la /app/auction-files
whoami
id
```

### Step 2: Fix Ownership and Permissions

In the n8n terminal:

```bash
# Make sure the directory is owned by node user
sudo chown -R node:node /app/auction-files

# Set proper permissions (read, write, execute for owner; read, execute for group/others)
chmod 755 /app/auction-files

# Or more permissive if needed
chmod 777 /app/auction-files
```

**Note**: If `sudo` doesn't work in the container, you might need to run this from the VPS:

```bash
# On VPS
docker exec -u root n8n-ugogs4kook4s804wgsssogoc chown -R node:node /app/auction-files
docker exec -u root n8n-ugogs4kook4s804wgsssogoc chmod 755 /app/auction-files
```

### Step 3: Verify

```bash
# Check permissions
ls -la /app/auction-files

# Test write as node user
touch /app/auction-files/test-write.txt
ls -la /app/auction-files/test-write.txt
```

### Step 4: Test Workflow

Run your workflow again - it should now be able to write files.

## Alternative: Check VPS Directory Permissions

Also verify the permissions on the VPS side:

```bash
# On VPS
ls -la /var/www/auction-files
sudo chown -R 1000:1000 /var/www/auction-files
sudo chmod 755 /var/www/auction-files
```

## Why This Happens

When you manually create files in the terminal, you might be running as root or a different user. The n8n workflow runs as the `node` user, which needs write permissions to the directory.





