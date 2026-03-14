#!/usr/bin/env python3
"""
Diagnostic script to check keywords data for multiple domains
"""

import asyncio
import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database
from models.domain_analysis import DetailedDataType

async def check_keywords_for_domains(domains: list):
    """Check keywords data for multiple domains"""
    await init_database()
    db = get_database()
    
    print(f"\n=== Checking Keywords Data for Multiple Domains ===\n")
    
    for domain in domains:
        print(f"\n{'='*60}")
        print(f"Domain: {domain}")
        print(f"{'='*60}\n")
        
        # Get keywords data
        detailed_data = await db.get_detailed_data(domain, DetailedDataType.KEYWORDS)
        
        if not detailed_data:
            print(f"❌ No keywords data found for {domain}")
            continue
        
        print(f"✅ Found keywords data")
        print(f"   - Domain Name (stored): {detailed_data.domain_name}")
        print(f"   - Data Type: {detailed_data.data_type.value}")
        print(f"   - Created At: {detailed_data.created_at}")
        print(f"   - Task ID: {detailed_data.task_id or 'N/A'}")
        
        json_data = detailed_data.json_data
        if isinstance(json_data, dict):
            items = json_data.get("items", [])
            total_count = json_data.get("total_count", 0)
            
            print(f"   - Total Count (stored): {total_count}")
            print(f"   - Actual Items Count: {len(items)}")
            
            if items:
                print(f"\n   First 5 Keywords:")
                for i, item in enumerate(items[:5], 1):
                    keyword_text = item.get("keyword_data", {}).get("keyword", "N/A")
                    rank = item.get("ranked_serp_element", {}).get("serp_item", {}).get("rank_absolute", "N/A")
                    print(f"      {i}. {keyword_text} (Rank: {rank})")
                
                # Check if keywords are actually related to the domain
                print(f"\n   Sample Keyword Details:")
                first_item = items[0]
                keyword_data = first_item.get("keyword_data", {})
                serp_item = first_item.get("ranked_serp_element", {}).get("serp_item", {})
                
                print(f"      - Keyword: {keyword_data.get('keyword', 'N/A')}")
                print(f"      - URL: {serp_item.get('url', 'N/A')}")
                print(f"      - Title: {serp_item.get('title', 'N/A')[:50]}...")
            else:
                print(f"   ⚠️  Items array is empty!")
        else:
            print(f"   ⚠️  json_data is not a dict: {type(json_data)}")
    
    # Check for duplicate data
    print(f"\n{'='*60}")
    print("Checking for Duplicate Data Across Domains")
    print(f"{'='*60}\n")
    
    all_keywords = {}
    for domain in domains:
        detailed_data = await db.get_detailed_data(domain, DetailedDataType.KEYWORDS)
        if detailed_data and isinstance(detailed_data.json_data, dict):
            items = detailed_data.json_data.get("items", [])
            keyword_texts = [
                item.get("keyword_data", {}).get("keyword", "")
                for item in items[:10]  # Check first 10
            ]
            all_keywords[domain] = keyword_texts
    
    # Compare keywords between domains
    if len(all_keywords) >= 2:
        domains_list = list(all_keywords.keys())
        for i in range(len(domains_list)):
            for j in range(i + 1, len(domains_list)):
                domain1 = domains_list[i]
                domain2 = domains_list[j]
                keywords1 = set(all_keywords[domain1])
                keywords2 = set(all_keywords[domain2])
                
                common = keywords1.intersection(keywords2)
                if common:
                    print(f"⚠️  WARNING: {domain1} and {domain2} share {len(common)} keywords:")
                    for keyword in list(common)[:5]:
                        print(f"      - {keyword}")
                    if len(common) > 5:
                        print(f"      ... and {len(common) - 5} more")
                else:
                    print(f"✅ {domain1} and {domain2} have different keywords")
    
    print(f"\n=== Check Complete ===\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_keywords_data.py <domain1> [domain2] ...")
        print("Example: python check_keywords_data.py giniloh.com example.com")
        sys.exit(1)
    
    domains = sys.argv[1:]
    asyncio.run(check_keywords_for_domains(domains))


























