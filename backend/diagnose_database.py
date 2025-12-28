#!/usr/bin/env python3
"""
Diagnose database connection issues
"""
import sys
import os
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def diagnose():
    """Diagnose database connection"""
    print("=" * 60)
    print("Database Connection Diagnostic")
    print("=" * 60)
    
    # Step 1: Check environment variables
    print("\n1. Checking environment variables...")
    try:
        from src.utils.config import get_settings
        settings = get_settings()
        print(f"   ✅ Settings loaded")
        print(f"   SUPABASE_URL: {settings.SUPABASE_URL[:50] if settings.SUPABASE_URL else 'NOT SET'}...")
        print(f"   SUPABASE_KEY: {'SET' if settings.SUPABASE_KEY else 'NOT SET'} (length: {len(settings.SUPABASE_KEY) if settings.SUPABASE_KEY else 0})")
        print(f"   SUPABASE_SERVICE_ROLE_KEY: {'SET' if settings.SUPABASE_SERVICE_ROLE_KEY else 'NOT SET'}")
        print(f"   SUPABASE_VERIFY_SSL: {getattr(settings, 'SUPABASE_VERIFY_SSL', True)}")
    except Exception as e:
        print(f"   ❌ Failed to load settings: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 2: Check database service initialization
    print("\n2. Checking database service initialization...")
    try:
        from src.services.database import DatabaseService
        db = DatabaseService()
        if db.client is None:
            print("   ❌ Database client is None")
            print("   This means _initialize_client() failed silently")
            return
        else:
            print("   ✅ Database client initialized")
    except Exception as e:
        print(f"   ❌ Failed to create DatabaseService: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 3: Test async init_database
    print("\n3. Testing async init_database()...")
    try:
        from src.services.database import init_database
        db = await init_database()
        if db.client is None:
            print("   ❌ Database client is None after init_database()")
            return
        print("   ✅ init_database() completed")
    except Exception as e:
        print(f"   ❌ init_database() failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 4: Test secrets table access
    print("\n4. Testing secrets table access...")
    try:
        result = db.client.table('secrets').select('id').limit(1).execute()
        print(f"   ✅ Secrets table accessible (found {len(result.data)} records)")
    except Exception as e:
        print(f"   ❌ Secrets table access failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 5: Test reports table access
    print("\n5. Testing reports table access...")
    try:
        result = db.client.table('reports').select('id').limit(1).execute()
        print(f"   ✅ Reports table accessible (found {len(result.data)} records)")
    except Exception as e:
        print(f"   ⚠️  Reports table access failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        print("   This would result in 'degraded' status, not 'unhealthy'")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 60)
    print("✅ All checks passed! Database should be healthy.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(diagnose())





