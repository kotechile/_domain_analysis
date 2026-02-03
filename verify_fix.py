import asyncio
import os
import httpx
from dotenv import load_dotenv

async def verify_fix():
    # Load environment variables
    load_dotenv('backend/.env')
    
    # Base URL
    base_url = "http://localhost:8001/api/v1"
    
    # 1. Trigger processing
    payload = {
        "bucket": "auction-csvs",
        "storage_path": "namesilo_export.csv",
        "filename": "namesilo_export.csv",
        "auction_site": "namesilo",
        "offering_type": "auction"
    }
    
    print(f"Triggering processing for {payload['filename']}...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(f"{base_url}/auctions/process-existing-upload", json=payload)
            response.raise_for_status()
            data = response.json()
            job_id = data.get('job_id')
            print(f"Triggered successfully. Job ID: {job_id}")
            
            # 2. Monitor progress
            print("Monitoring progress...")
            for _ in range(20):  # Check for 2 minutes
                await asyncio.sleep(10)
                progress_res = await client.get(f"{base_url}/auctions/upload-progress/{job_id}")
                progress_data = progress_res.json()
                
                status = progress_data.get('status')
                processed = progress_data.get('processed_records', 0)
                total = progress_data.get('total_records', 0)
                error = progress_data.get('error_message')
                
                print(f"Status: {status} | Progress: {processed}/{total}")
                
                if status == 'completed':
                    print("Job COMPLETED successfully!")
                    return True
                if status == 'failed':
                    print(f"Job FAILED: {error}")
                    return False
            
            print("Job timed out.")
            return False
            
        except Exception as e:
            print(f"Error during verification: {e}")
            return False

if __name__ == "__main__":
    asyncio.run(verify_fix())
