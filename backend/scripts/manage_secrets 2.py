#!/usr/bin/env python3
"""
Secrets management script for Domain Analysis System
Allows you to add, update, and view secrets stored in Supabase
"""

import asyncio
import json
import sys
from typing import Dict, Any, Optional
from pathlib import Path

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from services.secrets_service import get_secrets_service
from utils.config import get_settings


class SecretsManager:
    """CLI tool for managing secrets in Supabase"""
    
    def __init__(self):
        self.secrets_service = get_secrets_service()
    
    async def add_secret(self, service_name: str, credentials: Dict[str, Any]) -> bool:
        """Add or update a secret"""
        try:
            success = await self.secrets_service.update_secret(service_name, credentials)
            if success:
                print(f"✅ Successfully added/updated secret for {service_name}")
            else:
                print(f"❌ Failed to add/update secret for {service_name}")
            return success
        except Exception as e:
            print(f"❌ Error adding secret for {service_name}: {e}")
            return False
    
    async def get_secret(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get a secret"""
        try:
            secret = await self.secrets_service.get_secret(service_name)
            if secret:
                print(f"✅ Found secret for {service_name}")
                return secret
            else:
                print(f"❌ No secret found for {service_name}")
                return None
        except Exception as e:
            print(f"❌ Error getting secret for {service_name}: {e}")
            return None
    
    async def list_secrets(self) -> None:
        """List all available secrets"""
        try:
            # This would require a method to list all secrets
            # For now, we'll show the predefined services
            services = [
                'dataforseo', 'gemini', 'openai', 'wayback_machine',
                'google_trends', 'shareasale', 'impact', 'amazon_associates',
                'cj', 'partnerize', 'reddit', 'twitter', 'tiktok',
                'surfer_seo', 'frase', 'coschedule', 'google_docs',
                'notion', 'wordpress', 'linkup'
            ]
            
            print("📋 Available secret services:")
            for service in services:
                secret = await self.secrets_service.get_secret(service)
                status = "✅ Configured" if secret else "❌ Not configured"
                print(f"  {service}: {status}")
                
        except Exception as e:
            print(f"❌ Error listing secrets: {e}")
    
    async def clear_cache(self, service_name: Optional[str] = None) -> None:
        """Clear secrets cache"""
        try:
            await self.secrets_service.clear_cache(service_name)
            if service_name:
                print(f"✅ Cleared cache for {service_name}")
            else:
                print("✅ Cleared all secrets cache")
        except Exception as e:
            print(f"❌ Error clearing cache: {e}")


async def main():
    """Main CLI function"""
    if len(sys.argv) < 2:
        print("Usage: python manage_secrets.py <command> [args]")
        print("\nCommands:")
        print("  list                    - List all secrets")
        print("  get <service>           - Get secret for service")
        print("  add <service> <json>    - Add/update secret for service")
        print("  clear [service]         - Clear cache for service or all")
        print("\nExamples:")
        print("  python manage_secrets.py list")
        print("  python manage_secrets.py get dataforseo")
        print('  python manage_secrets.py add dataforseo \'{"login": "user", "password": "pass"}\'')
        print("  python manage_secrets.py clear")
        return
    
    manager = SecretsManager()
    command = sys.argv[1]
    
    if command == "list":
        await manager.list_secrets()
    
    elif command == "get":
        if len(sys.argv) < 3:
            print("❌ Please specify a service name")
            return
        service_name = sys.argv[2]
        secret = await manager.get_secret(service_name)
        if secret:
            print(f"\nSecret for {service_name}:")
            print(json.dumps(secret, indent=2))
    
    elif command == "add":
        if len(sys.argv) < 4:
            print("❌ Please specify service name and credentials JSON")
            return
        service_name = sys.argv[2]
        try:
            credentials = json.loads(sys.argv[3])
            await manager.add_secret(service_name, credentials)
        except json.JSONDecodeError:
            print("❌ Invalid JSON format for credentials")
    
    elif command == "clear":
        service_name = sys.argv[2] if len(sys.argv) > 2 else None
        await manager.clear_cache(service_name)
    
    else:
        print(f"❌ Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())




