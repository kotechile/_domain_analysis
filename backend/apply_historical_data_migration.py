#!/usr/bin/env python3
"""
Script to apply the historical_data migration to Supabase.
This leverages the 'exec_sql' RPC function which is expected to exist in the database.
"""

import sys
import os
from pathlib import Path
import asyncio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.database import DatabaseService
import structlog

logger = structlog.get_logger()

async def apply_migration():
    print("Initializing Database Service...")
    db = DatabaseService()
    
    if not db.client:
        print("❌ Failed to initialize Supabase client. check your .env settings.")
        return False

    migration_file = Path(__file__).parent / 'supabase_migrations' / '004_add_historical_data_column.sql'
    
    if not migration_file.exists():
        print(f"❌ Migration file not found at {migration_file}")
        return False
        
    print(f"Reading migration file: {migration_file.name}")
    with open(migration_file, 'r') as f:
        sql_content = f.read()
        
    print(f"Applying migration to add 'historical_data' column...")
    
    try:
        # Try to execute via RPC 'exec_sql'
        # This assumes the function exec_sql(sql text) exists in the public schema
        # which is common in Supabase setups for raw SQL execution
        response = db.client.rpc('exec_sql', {'sql': sql_content}).execute()
        
        print("✅ Migration applied successfully!")
        print("Column 'historical_data' has been added to the 'reports' table.")
        return True
        
    except Exception as e:
        print(f"❌ Error applying migration: {str(e)}")
        print("\nPossible reasons:")
        print("1. The 'exec_sql' RPC function does not exist (common in new Supabase projects)")
        print("2. Insufficient permissions")
        
        print("\n--- FALLBACK INSTRUCTIONS ---")
        print(f"Please execute the following SQL in your Supabase SQL Editor:")
        print("-" * 50)
        print(sql_content)
        print("-" * 50)
        return False

if __name__ == "__main__":
    asyncio.run(apply_migration())
