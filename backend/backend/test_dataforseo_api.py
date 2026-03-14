#!/usr/bin/env python3
"""
Test script for DataForSEO API calls to verify correct implementation
"""

import asyncio
import httpx
import sys
import os

# Add the src directory to the path
sys.path.append('src')

from src.utils.config import get_settings

async def test_dataforseo_api_calls():
    """Test DataForSEO API calls with correct format"""
    print("=== Testing DataForSEO API Calls ===")
    
    try:
        # Get settings
        settings = get_settings()
        api_url = settings.SUPABASE_URL  # This should be the DataForSEO API URL
        login = "your_login"  # Replace with actual credentials
        password = "your_password"  # Replace with actual credentials
        
        print(f"API URL: {api_url}")
        print(f"Login: {login}")
        
        # Note: Update these with your actual DataForSEO credentials
        if login == "your_login" or password == "your_password":
            print("⚠️  Please update the login and password variables with your actual DataForSEO credentials")
            print("   Get them from: https://app.dataforseo.com/api-access")
            return
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test 1: Backlinks Summary
            print("\n--- Testing Backlinks Summary API ---")
            post_data = {}
            post_data[len(post_data)] = {
                "target": "forbes.com",
                "internal_list_limit": 10,
                "include_subdomains": True,
                "backlinks_filters": ["dofollow", "=", True],
                "backlinks_status_type": "all"
            }
            
            try:
                response = await client.post(
                    f"{api_url}/v3/backlinks/summary/live",
                    auth=(login, password),
                    json=post_data
                )
                
                print(f"Status Code: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"DataForSEO Status Code: {data.get('status_code')}")
                    print(f"Status Message: {data.get('status_message')}")
                    print(f"Tasks Count: {data.get('tasks_count')}")
                    if data.get('status_code') == 20000:
                        print("✅ Backlinks Summary API call successful!")
                        if data.get('tasks') and data['tasks'][0].get('result'):
                            result = data['tasks'][0]['result'][0]
                            print(f"   Backlinks: {result.get('backlinks')}")
                            print(f"   Referring Domains: {result.get('referring_domains')}")
                    else:
                        print(f"❌ DataForSEO API error: {data.get('status_message')}")
                else:
                    print(f"❌ HTTP error: {response.status_code}")
                    print(f"Response: {response.text}")
            except Exception as e:
                print(f"❌ Backlinks Summary test failed: {e}")
            
            # Test 2: Backlinks Detailed
            print("\n--- Testing Backlinks Detailed API ---")
            backlinks_post_data = {}
            backlinks_post_data[len(backlinks_post_data)] = {
                "target": "forbes.com",
                "limit": 5,
                "mode": "as_is",
                "filters": ["dofollow", "=", True]
            }
            
            # Test 3: Domain Rank Overview
            print("\n--- Testing Domain Rank Overview API ---")
            domain_rank_post_data = {}
            domain_rank_post_data[len(domain_rank_post_data)] = {
                "target": "dataforseo.com",
                "language_name": "English",
                "location_code": 2840
            }
            
            try:
                response = await client.post(
                    f"{api_url}/v3/dataforseo_labs/google/domain_rank_overview/live",
                    auth=(login, password),
                    json=domain_rank_post_data
                )
                
                print(f"Status Code: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"DataForSEO Status Code: {data.get('status_code')}")
                    print(f"Status Message: {data.get('status_message')}")
                    if data.get('status_code') == 20000:
                        print("✅ Domain Rank Overview API call successful!")
                        if data.get('tasks') and data['tasks'][0].get('result'):
                            result = data['tasks'][0]['result'][0]
                            if result.get('items'):
                                metrics = result['items'][0].get('metrics', {})
                                organic = metrics.get('organic', {})
                                print(f"   Organic Keywords: {organic.get('count')}")
                                print(f"   Estimated Traffic Value: {organic.get('etv')}")
                                print(f"   Position 1-3: {organic.get('pos_1') + organic.get('pos_2_3', 0)}")
                    else:
                        print(f"❌ DataForSEO API error: {data.get('status_message')}")
                else:
                    print(f"❌ HTTP error: {response.status_code}")
                    print(f"Response: {response.text}")
            except Exception as e:
                print(f"❌ Domain Rank Overview test failed: {e}")
            
            # Test 4: Ranked Keywords
            print("\n--- Testing Ranked Keywords API ---")
            keywords_post_data = {}
            keywords_post_data[len(keywords_post_data)] = {
                "target": "dataforseo.com",
                "language_name": "English",
                "location_name": "United States",
                "load_rank_absolute": True,
                "limit": 3
            }
            
            try:
                response = await client.post(
                    f"{api_url}/v3/backlinks/backlinks/live",
                    auth=(login, password),
                    json=backlinks_post_data
                )
                
                print(f"Status Code: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"DataForSEO Status Code: {data.get('status_code')}")
                    print(f"Status Message: {data.get('status_message')}")
                    if data.get('status_code') == 20000:
                        print("✅ Backlinks Detailed API call successful!")
                        if data.get('tasks') and data['tasks'][0].get('result'):
                            result = data['tasks'][0]['result'][0]
                            print(f"   Total Count: {result.get('total_count')}")
                            print(f"   Items Count: {result.get('items_count')}")
                    else:
                        print(f"❌ DataForSEO API error: {data.get('status_message')}")
                else:
                    print(f"❌ HTTP error: {response.status_code}")
                    print(f"Response: {response.text}")
            except Exception as e:
                print(f"❌ Backlinks Detailed test failed: {e}")
            
            # Test 3: Ranked Keywords
            try:
                response = await client.post(
                    f"{api_url}/v3/dataforseo_labs/google/ranked_keywords/live",
                    auth=(login, password),
                    json=keywords_post_data
                )
                
                print(f"Status Code: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"DataForSEO Status Code: {data.get('status_code')}")
                    print(f"Status Message: {data.get('status_message')}")
                    if data.get('status_code') == 20000:
                        print("✅ Ranked Keywords API call successful!")
                        if data.get('tasks') and data['tasks'][0].get('result'):
                            result = data['tasks'][0]['result'][0]
                            print(f"   Total Count: {result.get('total_count')}")
                            print(f"   Items Count: {result.get('items_count')}")
                            if result.get('items'):
                                print(f"   Sample Keywords:")
                                for item in result['items'][:3]:
                                    keyword_data = item.get('keyword_data', {})
                                    keyword_info = keyword_data.get('keyword_info', {})
                                    print(f"     - {keyword_data.get('keyword')}: Vol={keyword_info.get('search_volume')}, Rank={item.get('ranked_serp_element', {}).get('serp_item', {}).get('rank_absolute')}")
                    else:
                        print(f"❌ DataForSEO API error: {data.get('status_message')}")
                else:
                    print(f"❌ HTTP error: {response.status_code}")
                    print(f"Response: {response.text}")
            except Exception as e:
                print(f"❌ Ranked Keywords test failed: {e}")
        
        print("\n=== Test Complete ===")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Note: This test requires valid DataForSEO credentials.")
    print("Update the login and password variables with your actual credentials.")
    asyncio.run(test_dataforseo_api_calls())
