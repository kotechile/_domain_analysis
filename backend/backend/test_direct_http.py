#!/usr/bin/env python3
"""
Test direct HTTP connection to Supabase
"""

import httpx
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_direct_http():
    """Test direct HTTP connection to Supabase"""
    try:
        print("🔧 Testing direct HTTP connection to Supabase...")
        
        from src.utils.config import get_settings
        
        settings = get_settings()
        print(f"✅ Configuration loaded successfully")
        print(f"SUPABASE_URL: {settings.SUPABASE_URL[:30]}...")
        print(f"SUPABASE_KEY: {settings.SUPABASE_KEY[:30]}...")
        
        # Test direct HTTP connection
        print("🔧 Making direct HTTP request...")
        response = httpx.get(
            f'{settings.SUPABASE_URL}/rest/v1/', 
            headers={
                'apikey': settings.SUPABASE_KEY, 
                'Authorization': f'Bearer {settings.SUPABASE_KEY}',
                'Content-Type': 'application/json'
            },
            timeout=10.0
        )
        
        print(f"HTTP Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Direct HTTP connection to Supabase successful!")
            print("✅ Your Supabase credentials are working correctly!")
            return True
        else:
            print(f"❌ HTTP connection failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ HTTP connection error: {e}")
        return False

if __name__ == "__main__":
    success = test_direct_http()
    sys.exit(0 if success else 1)




