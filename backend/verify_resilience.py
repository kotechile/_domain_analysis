import asyncio
import sys
import os
import psutil
from pathlib import Path
import uuid

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from api.routes.auctions import process_csv_upload_async
from services.database import init_database

async def verify_resilience():
    # Initialize DB (needed for progress updates)
    await init_database()
    
    test_file = 'large_test_auctions.csv'
    if not os.path.exists(test_file):
        print(f"Error: {test_file} not found")
        return

    file_size = os.path.getsize(test_file) / (1024 * 1024)
    print(f"\n=== Verification: Processing {test_file} ({file_size:.2f} MB) ===\n")
    
    process = psutil.Process()
    initial_mem = process.memory_info().rss / (1024 * 1024)
    print(f"Initial Memory Usage: {initial_mem:.2f} MB")
    
    job_id = f"test-resilience-{uuid.uuid4()}"
    
    try:
        # We'll use a mock database or just run it and let it fail on DB inserts if needed
        # but let's see how the parsing and scoring stages handle it first.
        # Actually, let's just trigger the real process_csv_upload_async
        # NOTE: This will attempt to insert records into your staging table!
        
        print("Starting background processing simulation...")
        await process_csv_upload_async(
            job_id=job_id,
            csv_content=test_file,
            filename=test_file,
            auction_site='namecheap',
            is_file=True
        )
        
        peak_mem = process.memory_info().rss / (1024 * 1024)
        print(f"Peak Memory Usage: {peak_mem:.2f} MB")
        print(f"Memory Increase: {peak_mem - initial_mem:.2f} MB")
        print("\n✅ Verification script completed.")
        
    except Exception as e:
        print(f"\n❌ Catching expected or unexpected error: {str(e)}")
        # It might fail on DB inserts if we don't have enough permissions or if staging is unique,
        # but the parsing/memory test is what we care about.

if __name__ == "__main__":
    asyncio.run(verify_resilience())
