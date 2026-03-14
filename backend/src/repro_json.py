import asyncio
import sys
import uuid
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from services.database import DatabaseService

async def test_json_path():
    db = DatabaseService()
    job_id = str(uuid.uuid4())
    print(f"Testing with job_id: {job_id}")
    
    # Mock some data that looks like GoDaddy JSON
    # GoDaddy JSON typically has a list of objects
    mock_data = [
        {"domainName": "repro-test-1.com", "endTime": "2025-12-31T23:59:59Z", "price": 100},
        {"domainName": "repro-test-2.com", "endTime": "2025-12-31T23:59:59Z", "price": 200}
    ]
    
    temp_json = Path("repro_test.json")
    with open(temp_json, 'w') as f:
        json.dump(mock_data, f)
    
    try:
        from api.routes.auctions import process_json_upload_async
        
        # We need to mock a few things if it fails but let's try calling it
        # Actually, let's just simulate the insertion logic from auctions.py manually
        # as it's easier than mocking all services.
        
        auction_dicts = []
        for i, item in enumerate(mock_data):
            auction_dict = {
                'domain': item['domainName'],
                'expiration_date': item['endTime'],
                'auction_site': 'godaddy',
                'job_id': job_id,
                'offer_type': 'auction'
            }
            auction_dicts.append(auction_dict)
            
        print(f"Prepared {len(auction_dicts)} records. First one: {auction_dicts[0]}")
        
        # Now try inserting
        batch_size = 5000
        for i in range(0, len(auction_dicts), batch_size):
            batch = auction_dicts[i:i + batch_size]
            staging_batch = [{k: v for k, v in r.items() if k != 'ranking'} for r in batch]
            print(f"Inserting staging_batch sample: {staging_batch[0]}")
            db.client.table('auctions_staging').insert(staging_batch).execute()
        
        # Check if they are there
        res = db.client.table('auctions_staging').select('job_id').eq('job_id', job_id).execute()
        print(f"Verification: Found {len(res.data)} records with job_id {job_id}")
        
        # Cleanup
        db.client.table('auctions_staging').delete().eq('job_id', job_id).execute()
        
    except Exception as e:
        print(f"Error in repro: {e}")
    finally:
        if temp_json.exists():
            temp_json.unlink()

if __name__ == "__main__":
    asyncio.run(test_json_path())
