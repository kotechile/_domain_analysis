#!/usr/bin/env python3
"""
Apply staging table migration for auctions CSV uploads
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import get_settings
import structlog

logger = structlog.get_logger()

def apply_migration():
    """Display migration SQL for manual application"""
    settings = get_settings()
    
    migration_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'supabase',
        'migrations',
        '20250128000000_create_auctions_staging_table.sql'
    )
    
    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    print("\n" + "=" * 70)
    print("Auctions Staging Table Migration")
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

if __name__ == "__main__":
    try:
        apply_migration()
    except Exception as e:
        logger.error("Failed to display migration", error=str(e), exc_info=True)
        sys.exit(1)














