
import asyncio
import os
import sys
from pprint import pprint

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.database import init_database, get_database
from services.secrets_service import get_secrets_service
from services.external_apis import LLMService

async def main():
    print("Initializing Database...")
    await init_database()
    
    secrets_service = get_secrets_service()
    
    print("\n--- Testing DataForSEO Credentials ---")
    dfs_creds = await secrets_service.get_dataforseo_credentials()
    if dfs_creds:
        print("Success! Retrieved DataForSEO credentials:")
        print(f"  Login: {dfs_creds.get('login')}")
        print(f"  Password: {'*' * 8} (masked)")
        print(f"  API URL: {dfs_creds.get('api_url')}")
    else:
        print("Failed to retrieve DataForSEO credentials.")

    print("\n--- Testing LLM Configuration ---")
    llm_config = await secrets_service.get_active_llm_config()
    if llm_config:
        print("Success! Retrieved Active LLM Config:")
        print(f"  Provider: {llm_config.get('provider')}")
        print(f"  Model: {llm_config.get('model_name')}")
        print(f"  API Key: {'*' * 8} (masked)")
    else:
        print("Failed to retrieve Active LLM Config.")

    print("\n--- Testing LLMService Provider Resolution ---")
    llm_service = LLMService()
    try:
        provider, api_key, model = await llm_service._get_provider_and_key()
        print(f"Resolved Provider: {provider}")
        print(f"Resolved Model: {model}")
        print(f"Resolved Key: {'*' * 8} (masked) if present: {bool(api_key)}")
    except Exception as e:
        print(f"Error resolving LLM provider: {e}")

if __name__ == "__main__":
    asyncio.run(main())
