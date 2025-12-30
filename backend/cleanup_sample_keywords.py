#!/usr/bin/env python3
"""
Script to identify and clean up sample/test keywords data from the database
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database
from models.domain_analysis import DetailedDataType

async def cleanup_sample_keywords(dry_run: bool = True):
    """Identify and optionally clean up sample keywords"""
    await init_database()
    db = get_database()
    
    print(f"\n=== {'DRY RUN: ' if dry_run else ''}Cleaning Up Sample Keywords ===\n")
    
    # Get all keywords data
    try:
        result = db.client.table('detailed_analysis_data').select('*').eq('data_type', 'keywords').execute()
        
        if not result.data:
            print("No keywords data found in database")
            return
        
        print(f"Found {len(result.data)} keyword records\n")
        
        domains_to_clean = []
        
        for record in result.data:
            domain = record['domain_name']
            json_data = record.get('json_data', {})
            items = json_data.get('items', [])
            
            if not items:
                continue
            
            # Check for sample keywords
            sample_keywords_found = []
            valid_keywords = []
            
            domain_lower = domain.lower().replace('www.', '')
            
            for item in items:
                serp_item = item.get("ranked_serp_element", {}).get("serp_item", {})
                url = serp_item.get("url", "")
                keyword_text = item.get("keyword_data", {}).get("keyword", "")
                
                if not url:
                    continue
                
                url_lower = url.lower()
                
                # Check if it's sample data
                if any(test_domain in url_lower for test_domain in [
                    'dataforseo.com',
                    'example.com',
                    'test.com',
                    'sample.com',
                    'demo.com'
                ]):
                    sample_keywords_found.append({
                        'keyword': keyword_text,
                        'url': url
                    })
                else:
                    valid_keywords.append(item)
            
            if sample_keywords_found:
                print(f"⚠️  {domain}:")
                print(f"   - Total items: {len(items)}")
                print(f"   - Sample keywords: {len(sample_keywords_found)}")
                print(f"   - Valid keywords: {len(valid_keywords)}")
                print(f"   - Sample keywords found:")
                for sample in sample_keywords_found[:3]:
                    print(f"      * {sample['keyword']} -> {sample['url']}")
                if len(sample_keywords_found) > 3:
                    print(f"      ... and {len(sample_keywords_found) - 3} more")
                
                if len(valid_keywords) == 0:
                    print(f"   ❌ ALL keywords are sample data - should be deleted")
                    domains_to_clean.append({
                        'domain': domain,
                        'action': 'delete',
                        'reason': 'All keywords are sample data'
                    })
                else:
                    print(f"   ⚠️  Has {len(valid_keywords)} valid keywords - should be cleaned")
                    domains_to_clean.append({
                        'domain': domain,
                        'action': 'clean',
                        'valid_count': len(valid_keywords),
                        'sample_count': len(sample_keywords_found)
                    })
                print()
        
        if not domains_to_clean:
            print("✅ No sample keywords found - database is clean!")
            return
        
        print(f"\n{'='*60}")
        print(f"Summary: {len(domains_to_clean)} domain(s) need cleanup")
        print(f"{'='*60}\n")
        
        if dry_run:
            print("DRY RUN - No changes made. Run with --execute to apply changes.")
        else:
            print("Executing cleanup...\n")
            
            for item in domains_to_clean:
                domain = item['domain']
                action = item['action']
                
                if action == 'delete':
                    # Delete the entire record
                    print(f"Deleting keywords data for {domain} (all sample data)")
                    await db.delete_detailed_data(domain, DetailedDataType.KEYWORDS)
                    print(f"✅ Deleted keywords data for {domain}")
                elif action == 'clean':
                    # Update with only valid keywords
                    detailed_data = await db.get_detailed_data(domain, DetailedDataType.KEYWORDS)
                    if detailed_data:
                        json_data = detailed_data.json_data.copy()
                        items = json_data.get('items', [])
                        
                        # Filter to only valid keywords
                        domain_lower = domain.lower().replace('www.', '')
                        valid_items = []
                        for keyword in items:
                            serp_item = keyword.get("ranked_serp_element", {}).get("serp_item", {})
                            url = serp_item.get("url", "")
                            if url:
                                url_lower = url.lower()
                                if not any(test_domain in url_lower for test_domain in [
                                    'dataforseo.com', 'example.com', 'test.com', 'sample.com', 'demo.com'
                                ]):
                                    valid_items.append(keyword)
                        
                        if valid_items:
                            json_data['items'] = valid_items
                            json_data['total_count'] = len(valid_items)
                            json_data['items_count'] = len(valid_items)
                            
                            detailed_data.json_data = json_data
                            await db.save_detailed_data(detailed_data)
                            print(f"✅ Cleaned keywords data for {domain}: {len(valid_items)} valid keywords kept")
                        else:
                            # No valid keywords, delete
                            await db.delete_detailed_data(domain, DetailedDataType.KEYWORDS)
                            print(f"✅ Deleted keywords data for {domain} (no valid keywords after cleaning)")
        
        print(f"\n=== Cleanup Complete ===\n")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    dry_run = '--execute' not in sys.argv
    asyncio.run(cleanup_sample_keywords(dry_run=dry_run))






















