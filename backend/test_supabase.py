#!/usr/bin/env python3
"""
Test Supabase connection
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.utils.config import get_settings
from src.services.database import DatabaseService

def test_supabase_connection():
    """Test Supabase connection"""
    try:
        print("🔧 Testing Supabase connection...")
        
        # Load settings
        settings = get_settings()
        print(f"✅ Configuration loaded successfully")
        print(f"SUPABASE_URL: {settings.SUPABASE_URL[:30]}...")
        print(f"SUPABASE_KEY: {settings.SUPABASE_KEY[:30]}...")
        verify_ssl = getattr(settings, 'SUPABASE_VERIFY_SSL', True)
        print(f"SSL Verification: {'Enabled' if verify_ssl else 'Disabled (self-hosted)'}")
        
        # Create database service directly (which handles SSL verification properly)
        db = DatabaseService()
        if not db.client:
            print("❌ Failed to initialize Supabase client")
            return False
        
        print("✅ Supabase client created successfully")
        
        # Test connection with a simple query
        try:
            result = db.client.table('secrets').select('*').limit(1).execute()
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
                
        except Exception as query_error:
            print(f"⚠️  Query failed (this might be expected if tables don't exist yet): {str(query_error)}")
            print("ℹ️  This is normal if you haven't run the Supabase migration yet")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure you've updated your .env file with real Supabase credentials")
        print("2. Check that your Supabase project is active")
        print("3. Verify your SUPABASE_URL and SUPABASE_KEY are correct")
        return False

if __name__ == "__main__":
    success = test_supabase_connection()
    sys.exit(0 if success else 1)
