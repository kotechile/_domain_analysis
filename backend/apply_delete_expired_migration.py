#!/usr/bin/env python3
"""
Script to apply the delete_expired_auctions function migration.

This migration creates a SQL function to reliably delete expired auctions.
"""

import sys
import os

# Get the migration file path
migration_file = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'supabase',
    'migrations',
    '20250131000008_create_delete_expired_auctions_function.sql'
)

if not os.path.exists(migration_file):
    print(f"ERROR: Migration file not found: {migration_file}")
    sys.exit(1)

# Read the migration SQL
with open(migration_file, 'r') as f:
    migration_sql = f.read()

print("=" * 80)
print("DELETE EXPIRED AUCTIONS FUNCTION MIGRATION")
print("=" * 80)
print()
print("This migration creates a SQL function to delete expired auctions.")
print("The function deletes all records where expiration_date < NOW().")
print()
print("To apply this migration:")
print()
print("1. Open Supabase Studio (your Supabase dashboard)")
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
print()
print("After applying, expired records will be automatically deleted")
print("after each CSV upload. You can also manually trigger deletion")
print("using: POST /api/v1/auctions/delete-expired")
print()
print("=" * 80)





