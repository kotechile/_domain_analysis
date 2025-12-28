#!/usr/bin/env python3
"""
Script to apply the batched merge function migration.

This migration updates the merge_auctions_from_staging function to process
records in batches, preventing statement timeouts on large datasets.
"""

import os
import sys

# Get the migration file path
migration_file = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'supabase',
    'migrations',
    '20250128000001_update_merge_function_batched.sql'
)

if not os.path.exists(migration_file):
    print(f"ERROR: Migration file not found: {migration_file}")
    sys.exit(1)

# Read the migration SQL
with open(migration_file, 'r') as f:
    migration_sql = f.read()

print("=" * 80)
print("BATCHED MERGE FUNCTION MIGRATION")
print("=" * 80)
print()
print("This migration updates the merge_auctions_from_staging function to")
print("process records in batches of 50,000 to prevent statement timeouts.")
print()
print("To apply this migration:")
print()
print("1. Open Supabase Studio: https://supabase.com/dashboard")
print("2. Go to SQL Editor")
print("3. Copy and paste the SQL below:")
print()
print("-" * 80)
print(migration_sql)
print("-" * 80)
print()
print("4. Click 'Run' to execute the migration")
print()
print("Alternatively, if you have psql access:")
print(f"  psql $DATABASE_URL -f {migration_file}")
print()
print("=" * 80)









