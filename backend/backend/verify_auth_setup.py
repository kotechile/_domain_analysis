import requests
import sys

def test_auth_endpoint():
    print("Testing Auth Endpoint Protection...")
    try:
        # 1. Test without token (should fail with 401 or 403)
        # Note: server needs to be running. I'll assume port 8000.
        response = requests.get("http://localhost:8000/api/v1/auth/me")
        
        if response.status_code == 401:
            print("SUCCESS: Endpoint protected (Received 401 Unauthorized as expected without token)")
        elif response.status_code == 200:
            print("FAILURE: Endpoint accessible without token!")
        else:
            print(f"WARNING: Unexpected status code: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to backend. Is it running?")

if __name__ == "__main__":
    test_auth_endpoint()
