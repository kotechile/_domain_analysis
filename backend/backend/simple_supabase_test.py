#!/usr/bin/env python3
"""
Simple Supabase connection test
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_supabase_simple():
    """Simple Supabase connection test"""
    try:
        print("🔧 Testing Supabase connection...")
        
        # Import after path setup
        from src.utils.config import get_settings
        from supabase import create_client
        
        # Load settings
        settings = get_settings()
        print(f"✅ Configuration loaded successfully")
        print(f"SUPABASE_URL: {settings.SUPABASE_URL[:30]}...")
        print(f"SUPABASE_KEY: {settings.SUPABASE_KEY[:30]}...")
        
        # Test basic client creation
        print("🔧 Creating Supabase client...")
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        print("✅ Supabase client created successfully")
        
        # Test a simple query
        print("🔧 Testing database query...")
        result = supabase.table('secrets').select('*').limit(1).execute()
        print("✅ Supabase connection successful")
        print(f"Query result: {len(result.data)} records found")
        
        if result.data:
            print("📊 Sample data:")
            for key, value in result.data[0].items():
                if key == 'credentials':
                    print(f"  {key}: [REDACTED]")
                else:
                    print(f"  {key}: {value}")
        else:
            print("ℹ️  No data found in secrets table (this is normal if you haven't added any secrets yet)")
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_supabase_simple()
    sys.exit(0 if success else 1)




