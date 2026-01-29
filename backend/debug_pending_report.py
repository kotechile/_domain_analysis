
import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from services.database import get_database, init_database

async def main():
    try:
        # Initialize database
        await init_database()
        db = get_database()
        
        domain = "giniloh.com"
        
        # Get report
        print(f"Fetching report for {domain}...")
        report = await db.get_report(domain)
        
        if report:
            print(f"Report found:")
            print(f"Status: {report.status}")
            print(f"Phase: {report.analysis_phase}")
            print(f"Error Message: {report.error_message}")
            print(f"Created At: {report.analysis_timestamp}")
            print(f"Progress Data: {report.progress_data}")
            print(f"Historical Data Present: {report.historical_data is not None}")
            if report.historical_data:
                # Use model_dump instead of dict
                data = report.historical_data.model_dump()
                print(f"Historical Keys: {data.keys()}")
                if data.get('rank_overview'):
                    print(f"Rank Overview Keywords Count: {len(data['rank_overview'].get('organic_keywords_count', []))}")
                    print(f"Rank Overview Traffic Value Count: {len(data['rank_overview'].get('organic_traffic_value', []))}")
                if data.get('traffic_analytics'):
                    print(f"Traffic Visits Count: {len(data['traffic_analytics'].get('visits_history', []))}")
            print(f"Detailed Data Available: {report.detailed_data_available}")
            
            # Check detailed data tables
            # detailed_data = await db.client.table("detailed_analysis_data").select("*").eq("domain_name", domain).execute()
            # print(f"Detailed Data Records: {len(detailed_data.data)}")
        else:
            print("Report not found")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
