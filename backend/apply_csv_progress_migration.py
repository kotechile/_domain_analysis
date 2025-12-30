#!/usr/bin/env python3
"""
Script to apply csv_upload_progress table migration to self-hosted Supabase
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from supabase import create_client
from utils.config import get_settings
import structlog

logger = structlog.get_logger()

def apply_migration():
    """Apply the csv_upload_progress table migration"""
    
    settings = get_settings()
    
    # Read migration file
    migration_file = Path(__file__).parent.parent / 'supabase' / 'migrations' / '20250127000000_create_csv_upload_progress_table.sql'
    
    if not migration_file.exists():
        logger.error("Migration file not found", path=str(migration_file))
        return False
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    try:
        # Create Supabase client
        from supabase.lib.client_options import SyncClientOptions
        import httpx
        
        # Configure HTTP client with SSL verification setting
        if not getattr(settings, 'SUPABASE_VERIFY_SSL', True):
            custom_client = httpx.Client(verify=False)
            client_options = SyncClientOptions(httpx_client=custom_client)
            client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY,
                options=client_options
            )
        else:
            client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY
            )
        
        logger.info("Connected to Supabase", url=settings.SUPABASE_URL)
        
        print("\n" + "=" * 70)
        print("CSV Upload Progress Table Migration")
        print("=" * 70)
        print("\n⚠️  Note: The Supabase Python client doesn't support direct SQL execution.")
        print("You have two options to apply this migration:\n")
        
        print("OPTION 1: Via Supabase Studio (Recommended)")
        print("-" * 70)
        print(f"1. Open Supabase Studio: {settings.SUPABASE_URL}")
        print("2. Navigate to: SQL Editor (in the left sidebar)")
        print("3. Click 'New Query'")
        print("4. Copy and paste the SQL below")
        print("5. Click 'Run' to execute\n")
        
        print("OPTION 2: Via psql (Command Line)")
        print("-" * 70)
        print("Connect to your PostgreSQL database and run the SQL:")
        print("  psql -h <your-host> -U postgres -d postgres")
        print("  (Then paste the SQL below)\n")
        
        print("=" * 70)
        print("MIGRATION SQL:")
        print("=" * 70)
        print(migration_sql)
        print("=" * 70)
        
        logger.info("Migration instructions displayed")
        return True
        
    except Exception as e:
        logger.error("Failed to connect to Supabase", error=str(e))
        print("\n❌ Error connecting to Supabase:", str(e))
        print("\nPlease check your .env configuration:")
        print(f"  SUPABASE_URL={settings.SUPABASE_URL}")
        print("  SUPABASE_KEY=...")
        print("  SUPABASE_SERVICE_ROLE_KEY=...")
        print("\nThen apply the migration manually using Option 1 or 2 above.")
        return False

if __name__ == '__main__':
    print("=" * 70)
    print("CSV Upload Progress Migration")
    print("=" * 70)
    
    success = apply_migration()
    
    if not success:
        print("\n" + "=" * 70)
        print("MANUAL MIGRATION REQUIRED")
        print("=" * 70)
        print("\nFor self-hosted Supabase, apply the migration via:")
        print("1. Supabase Studio → SQL Editor")
        print("2. Or via psql connection to your PostgreSQL database")
        print("\nMigration file location:")
        migration_file = Path(__file__).parent.parent / 'supabase' / 'migrations' / '20250127000000_create_csv_upload_progress_table.sql'
        print(f"   {migration_file}")
        sys.exit(1)
    else:
        print("\n✅ Migration SQL displayed above. Please apply it manually.")
        print("   After applying, the CSV upload progress tracking will work.")
        sys.exit(0)














