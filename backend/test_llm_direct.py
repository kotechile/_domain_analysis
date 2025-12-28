#!/usr/bin/env python3
"""
Test LLM service directly to identify the issue
"""
import asyncio
import sys
import os

# Add the src directory to the path
sys.path.append('src')

from services.external_apis import LLMService

async def test_llm_service():
    """Test the LLM service directly"""
    print("Testing LLM service...")
    
    try:
        llm_service = LLMService()
        
        # Test health check
        print("1. Testing health check...")
        health = await llm_service.health_check()
        print(f"   Health check result: {health}")
        
        if not health:
            print("   ❌ LLM service is not healthy")
            return
        
        # Test getting provider and key
        print("2. Testing provider and key...")
        provider, api_key = await llm_service._get_provider_and_key()
        print(f"   Provider: {provider}")
        print(f"   API Key: {'***' + api_key[-4:] if api_key else 'None'}")
        
        if not provider or not api_key:
            print("   ❌ No provider or API key available")
            return
        
        # Test with minimal data
        print("3. Testing analysis generation...")
        test_data = {
            "analytics": {"domain_rank": 50},
            "backlinks_summary": {"backlinks": 100, "referring_domains": 50},
            "backlinks": {"items": []},
            "keywords": {"items": []},
            "wayback": {}
        }
        
        print("   Calling generate_analysis with timeout...")
        try:
            result = await asyncio.wait_for(
                llm_service.generate_analysis("test.com", test_data),
                timeout=15.0
            )
            print(f"   ✅ Analysis generated: {result is not None}")
            if result:
                print(f"   Summary: {result.get('summary', 'No summary')[:100]}...")
        except asyncio.TimeoutError:
            print("   ❌ LLM service timed out after 15 seconds")
        except Exception as e:
            print(f"   ❌ LLM service failed: {e}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_llm_service())
