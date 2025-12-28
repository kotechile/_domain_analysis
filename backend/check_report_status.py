#!/usr/bin/env python3
"""
Check the report status for a domain
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.database import get_database, init_database

async def check_report_status(domain: str):
    """Check report status"""
    await init_database()
    db = get_database()
    
    print(f"\n=== Report Status for {domain} ===\n")
    
    report = await db.get_report(domain)
    if report:
        print(f"Status: {report.status}")
        print(f"Phase: {report.analysis_phase}")
        print(f"Progress: {report.progress_info}")
        print(f"Error: {report.error_message or 'None'}")
        print(f"Timestamp: {report.analysis_timestamp}")
    else:
        print("❌ No report found")
    
    print("\n=== Check Complete ===\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_report_status.py <domain>")
        sys.exit(1)
    
    domain = sys.argv[1]
    asyncio.run(check_report_status(domain))

















