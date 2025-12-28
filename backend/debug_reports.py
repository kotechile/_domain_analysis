#!/usr/bin/env python3
"""
Debug reports table to check for dataforseo.com
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.database import init_database, get_database

async def debug_reports():
    """Debug reports table"""
    await init_database()
    db = get_database()
    
    print("Checking reports for dataforseo.com...")
    
    # Check if there are any reports for dataforseo.com
    result = db.client.table('reports').select('*').eq('domain_name', 'dataforseo.com').execute()
    print(f'Reports found for dataforseo.com: {len(result.data)}')
    
    if result.data:
        for report in result.data:
            print(f'Report ID: {report["id"]}')
            print(f'Status: {report["status"]}')
            print(f'Created: {report["created_at"]}')
            print(f'Updated: {report["updated_at"]}')
            print(f'Analysis timestamp: {report.get("analysis_timestamp")}')
    else:
        print('No reports found for dataforseo.com')
        
        # Check all reports
        all_reports = db.client.table('reports').select('domain_name, status, created_at').order('created_at', desc=True).limit(5).execute()
        print(f'\nRecent reports:')
        for report in all_reports.data:
            print(f'- {report["domain_name"]} ({report["status"]}) - {report["created_at"]}')

if __name__ == "__main__":
    asyncio.run(debug_reports())








