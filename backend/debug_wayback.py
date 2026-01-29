
import asyncio
import httpx
import json

async def check_wayback(url_pattern, match_type=None):
    base_url = "http://web.archive.org/cdx/search/cdx"
    params = {
        "url": url_pattern,
        "output": "json",
        "limit": 5,
        "collapse": "timestamp:8"
    }
    if match_type:
        params["matchType"] = match_type
        
    print(f"Checking URL: {url_pattern} | MatchType: {match_type}...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(base_url, params=params)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"Rows returned: {len(data)}")
                    if len(data) > 0:
                        print(f"Header: {data[0]}")
                    if len(data) > 1:
                        print(f"Sample: {data[1]}")
                except:
                    print(f"Failed to parse JSON. Content: {response.text[:100]}...")
            else:
                print(f"Error content: {response.text[:100]}...")
    except Exception as e:
        print(f"Exception: {e}")
    print("-" * 50)

async def main():
    domain = "giniloh.com"
    
    # Test 1: Current logic (http://domain)
    await check_wayback(f"http://{domain}")
    
    # Test 2: Current logic (https://domain)
    await check_wayback(f"https://{domain}")
    
    # Test 3: Domain match
    await check_wayback(domain, match_type="domain")
    
    # Test 4: Wildcard *.domain
    await check_wayback(f"*.{domain}")

if __name__ == "__main__":
    asyncio.run(main())
