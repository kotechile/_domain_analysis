#!/usr/bin/env python3
"""
Script to apply the COMPLETE database schema to Supabase.
This ensures all tables (reports, cache, namecheap, etc.) exist.
It leverages the 'exec_sql' RPC function.
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
        print("❌ Failed to initialize Supabase client. Check your .env settings.")
        return False

    migration_file = Path(__file__).parent / 'supabase_migrations' / '005_ensure_complete_schema.sql'
    
    if not migration_file.exists():
        print(f"❌ Migration file not found at {migration_file}")
        return False
        
    print(f"Reading migration file: {migration_file.name}")
    with open(migration_file, 'r') as f:
        sql_content = f.read()
        
    print(f"Applying complete schema migration...")
    
    try:
        # Try to execute via RPC 'exec_sql'
        response = db.client.rpc('exec_sql', {'sql': sql_content}).execute()
        
        print("✅ Schema applied successfully!")
        print("All tables (reports, namecheap_domains, etc.) have been verified/created.")
        return True
        
    except Exception as e:
        print(f"❌ Error applying migration via RPC: {str(e)}")
        print("\n--- MANUAL INSTRUCTIONS ---")
        print("Please copy the content of the SQL file and run it in Supabase SQL Editor:")
        print(f"File: {migration_file}")
        return False

if __name__ == "__main__":
    asyncio.run(apply_migration())
