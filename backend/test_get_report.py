#!/usr/bin/env python3
"""
Test get_report method directly
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.database import init_database, get_database

async def test_get_report():
    """Test get_report method"""
    await init_database()
    db = get_database()
    
    print("Testing get_report for dataforseo.com...")
    
    try:
        report = await db.get_report('dataforseo.com')
        if report:
            print(f"✅ Report found!")
            print(f"Domain: {report.domain_name}")
            print(f"Status: {report.status}")
            print(f"Analysis timestamp: {report.analysis_timestamp}")
            print(f"DataForSEO metrics: {report.data_for_seo_metrics is not None}")
            print(f"Wayback summary: {report.wayback_machine_summary is not None}")
            print(f"LLM analysis: {report.llm_analysis is not None}")
        else:
            print("❌ Report not found")
    except Exception as e:
        print(f"❌ Error getting report: {e}")

if __name__ == "__main__":
    asyncio.run(test_get_report())








