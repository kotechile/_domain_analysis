# Auctions Table Migration Guide

## Overview

This guide explains how to apply the `auctions` table migration to your self-hosted Supabase instance on Hostinger VPS.

## Migration File

**Location:** `supabase/migrations/20250125000002_create_auctions_table.sql`

This migration creates:
- `auctions` table with all required fields
- Indexes for performance
- Row Level Security (RLS) policies
- Updated_at trigger

## Method 1: Via Supabase Studio (Recommended)

### Steps:

1. **Access Supabase Studio**
   - Open your Supabase dashboard: `https://sbdomain.aichieve.net` (or your configured URL)
   - Log in with your admin credentials

2. **Navigate to SQL Editor**
   - Click on **"SQL Editor"** in the left sidebar
   - Click **"New Query"** button

3. **Copy Migration SQL**
   - Open the migration file: `supabase/migrations/20250125000002_create_auctions_table.sql`
   - Copy the entire contents

4. **Paste and Execute**
   - Paste the SQL into the SQL Editor
   - Click **"Run"** button (or press `Ctrl+Enter` / `Cmd+Enter`)

5. **Verify Success**
   - You should see a success message
   - Check the **"Table Editor"** to confirm the `auctions` table exists

## Method 2: Via psql (Command Line)

### Prerequisites:
- SSH access to your Hostinger VPS
- PostgreSQL client installed (`psql`)

### Steps:

1. **Connect to PostgreSQL**
   ```bash
   psql -h sbdomain.aichieve.net -U postgres -d postgres -p 5434
   ```
   (Enter your PostgreSQL password when prompted)

2. **Run the Migration**
   ```bash
   \i /path/to/supabase/migrations/20250125000002_create_auctions_table.sql
   ```
   
   Or copy-paste the SQL directly:
   ```sql
   -- Copy the entire contents of the migration file here
   ```

3. **Verify**
   ```sql
   \dt auctions
   ```
   Should show the auctions table.

## Method 3: Using Python Script

A helper script is available to display the migration SQL:

```bash
cd backend
source venv/bin/activate  # or your virtual environment
python apply_auctions_migration.py
```

This script will:
- Connect to your Supabase instance
- Display the migration SQL
- Provide instructions for applying it

## Verification

After applying the migration, verify it worked:

### Via Supabase Studio:
1. Go to **Table Editor**
2. Look for `auctions` table
3. Check that it has the following columns:
   - `id` (UUID)
   - `domain` (VARCHAR)
   - `expiration_date` (TIMESTAMP)
   - `auction_site` (VARCHAR)
   - `ranking` (INTEGER)
   - `score` (DECIMAL)
   - `preferred` (BOOLEAN)
   - `has_statistics` (BOOLEAN)
   - `source_data` (JSONB)
   - `created_at`, `updated_at` (TIMESTAMP)

### Via SQL:
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'auctions'
ORDER BY ordinal_position;
```

### Check Indexes:
```sql
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'auctions';
```

Should show 7 indexes:
- `idx_auctions_expiration`
- `idx_auctions_preferred`
- `idx_auctions_has_stats`
- `idx_auctions_domain`
- `idx_auctions_auction_site`
- `idx_auctions_score`
- `idx_auctions_ranking`

### Check RLS Policies:
```sql
SELECT policyname, cmd, qual 
FROM pg_policies 
WHERE tablename = 'auctions';
```

Should show 2 policies:
- "Public can read auctions"
- "Service role can manage auctions"

## Troubleshooting

### Error: "relation already exists"
If you see this error, the table might already exist. Check if it was partially created:
```sql
SELECT * FROM auctions LIMIT 1;
```

If the table exists but is incomplete, you may need to drop it first:
```sql
DROP TABLE IF EXISTS auctions CASCADE;
```
Then re-run the migration.

### Error: "function update_updated_at_column() does not exist"
This function should have been created by the base tables migration. If it's missing, run:
```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';
```

### Connection Issues
If you can't connect to Supabase:
1. Check your `.env` file has correct credentials
2. Verify the Supabase service is running on your VPS
3. Check firewall rules allow connections on port 5434 (PostgreSQL) or 443/8000 (API)

## Next Steps

After successfully applying the migration:

1. **Test the Backend**
   ```bash
   cd backend
   python -c "from src.services.database import get_database; import asyncio; asyncio.run(get_database().truncate_auctions())"
   ```
   (This should run without errors)

2. **Test via API**
   - Start your backend server
   - Try uploading a CSV via the `/api/v1/auctions/upload-csv` endpoint

3. **Check Frontend**
   - Navigate to `/auctions` page
   - Verify the page loads without errors

## Rollback (If Needed)

If you need to rollback the migration:

```sql
DROP TABLE IF EXISTS auctions CASCADE;
```

**Warning:** This will delete all data in the auctions table!

## Support

If you encounter issues:
1. Check the Supabase logs on your VPS
2. Verify your database connection settings
3. Ensure all previous migrations have been applied
4. Check that the `update_updated_at_column()` function exists





















