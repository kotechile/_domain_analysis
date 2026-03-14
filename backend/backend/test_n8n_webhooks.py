#!/usr/bin/env python3
"""
Test N8N webhooks to diagnose issues
"""
import asyncio
import httpx
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_n8n_config():
    """Get N8N configuration from environment"""
    return {
        "enabled": os.getenv("N8N_ENABLED", "false").lower() == "true",
        "webhook_url": os.getenv("N8N_WEBHOOK_URL", ""),
        "webhook_url_summary": os.getenv("N8N_WEBHOOK_URL_SUMMARY", ""),
        "callback_url": os.getenv("N8N_CALLBACK_URL", ""),
        "use_for_backlinks": os.getenv("N8N_USE_FOR_BACKLINKS", "false").lower() == "true",
        "use_for_summary": os.getenv("N8N_USE_FOR_SUMMARY", "false").lower() == "true",
    }

async def test_n8n_webhook(webhook_url: str, payload: dict, name: str):
    """Test an N8N webhook"""
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print(f"{'='*60}")
    print(f"URL: {webhook_url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print(f"\nSending request...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(webhook_url, json=payload)
            
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"\nResponse Body:")
            try:
                response_json = response.json()
                print(json.dumps(response_json, indent=2))
            except:
                print(response.text[:1000])
            
            if response.status_code in [200, 201, 202]:
                print(f"\n✅ {name} webhook is working!")
                return True
            else:
                print(f"\n❌ {name} webhook returned error status {response.status_code}")
                return False
                
    except httpx.TimeoutException:
        print(f"\n❌ {name} webhook timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"\n❌ {name} webhook failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    config = get_n8n_config()
    
    print("N8N Configuration:")
    print(f"  N8N_ENABLED: {config['enabled']}")
    print(f"  N8N_WEBHOOK_URL: {config['webhook_url']}")
    print(f"  N8N_WEBHOOK_URL_SUMMARY: {config['webhook_url_summary']}")
    print(f"  N8N_CALLBACK_URL: {config['callback_url']}")
    print(f"  N8N_USE_FOR_BACKLINKS: {config['use_for_backlinks']}")
    print(f"  N8N_USE_FOR_SUMMARY: {config['use_for_summary']}")
    
    # Test summary webhook
    summary_payload = {
        "domain": "test.com",
        "callback_url": config['callback_url'],
        "request_id": "test-summary-123",
        "type": "summary"
    }
    
    summary_ok = await test_n8n_webhook(
        config['webhook_url_summary'],
        summary_payload,
        "Summary Backlinks"
    )
    
    # Test detailed webhook
    detailed_payload = {
        "domain": "test.com",
        "limit": 100,
        "callback_url": config['callback_url'],
        "request_id": "test-detailed-123",
        "type": "detailed"
    }
    
    detailed_ok = await test_n8n_webhook(
        config['webhook_url'],
        detailed_payload,
        "Detailed Backlinks"
    )
    
    print(f"\n{'='*60}")
    print("Summary:")
    print(f"{'='*60}")
    print(f"Summary Webhook: {'✅ OK' if summary_ok else '❌ FAILED'}")
    print(f"Detailed Webhook: {'✅ OK' if detailed_ok else '❌ FAILED'}")
    
    if not summary_ok or not detailed_ok:
        print("\n⚠️  One or more webhooks are failing!")
        print("   Check N8N Executions tab for detailed error messages.")
        print("   Common issues:")
        print("   - DataForSEO node not configured correctly")
        print("   - Webhook expressions incorrect (check $json.body.domain)")
        print("   - IF node conditions incorrect")
        print("   - HTTP Request node URL expressions incorrect")

if __name__ == "__main__":
    asyncio.run(main())

