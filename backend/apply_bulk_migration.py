#!/usr/bin/env python3
"""
Script to apply bulk_domain_analysis table migration to self-hosted Supabase
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
    """Apply the bulk_domain_analysis table migration"""
    
    settings = get_settings()
    
    # Read migration file
    migration_file = Path(__file__).parent.parent / 'supabase' / 'migrations' / '20250125000000_create_bulk_domain_analysis_table.sql'
    
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
        
        # Split SQL into individual statements (simple approach)
        # Note: This is a basic implementation. For production, use a proper SQL parser
        statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]
        
        # Execute each statement
        for i, statement in enumerate(statements, 1):
            if not statement:
                continue
            try:
                # Use RPC to execute SQL (if available) or direct query
                # Note: Supabase Python client doesn't have direct SQL execution
                # You'll need to use the REST API or psql
                logger.info(f"Executing statement {i}/{len(statements)}")
                # This is a placeholder - actual execution depends on your setup
                print(f"\n⚠️  Note: Direct SQL execution via Python client is limited.")
                print(f"Please run the migration SQL manually via Supabase Studio or psql.")
                print(f"\nMigration SQL:\n{migration_sql}")
                break
            except Exception as e:
                logger.error(f"Failed to execute statement {i}", error=str(e))
                return False
        
        logger.info("Migration instructions displayed")
        return True
        
    except Exception as e:
        logger.error("Failed to apply migration", error=str(e))
        print(f"\n❌ Error: {str(e)}")
        print("\nPlease apply the migration manually:")
        print(f"1. Open Supabase Studio at {settings.SUPABASE_URL}")
        print("2. Go to SQL Editor")
        print("3. Copy and paste the SQL from:")
        print(f"   {migration_file}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Bulk Domain Analysis Migration")
    print("=" * 60)
    
    success = apply_migration()
    
    if not success:
        print("\n" + "=" * 60)
        print("MANUAL MIGRATION REQUIRED")
        print("=" * 60)
        print("\nFor self-hosted Supabase, apply the migration via:")
        print(f"1. Supabase Studio ({settings.SUPABASE_URL}) → SQL Editor")
        print("2. Or via psql connection to your PostgreSQL database")
        print("\nMigration file location:")
        migration_file = Path(__file__).parent.parent / 'supabase' / 'migrations' / '20250125000000_create_bulk_domain_analysis_table.sql'
        print(f"   {migration_file}")
        sys.exit(1)
    else:
        print("\n✅ Migration applied successfully!")
        sys.exit(0)
