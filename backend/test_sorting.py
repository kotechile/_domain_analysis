
import asyncio
import os
import sys
from datetime import datetime
from uuid import UUID

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'backend/src'))

from services.database import get_database, init_database

async def test_sorting():
    await init_database()
    db = get_database()
    
    print("Testing sort by domain_rating...")
    try:
        # Simulate fetchAuctions call from frontend
        # sort_by='domain_rating', order='desc', limit=50, offset=0
        
        # We need to mock the filters
        filters = {
            'scored': True, # Scored only
            'expiration_from_date': datetime.utcnow().isoformat()
        }
        
        # Call the method directly
        from services.auctions_service import AuctionsService
        service = AuctionsService()
        
        results = await db.get_auctions_with_statistics(
            filters=filters,
            sort_by='domain_rating',
            order='desc',
            limit=50,
            offset=0
        )
        
        auctions = results.get('auctions', [])
        print(f"Results Count: {len(auctions)}")
        if auctions:
            print(f"Top Result: {auctions[0]['domain']} (DR: {auctions[0].get('domain_rating')})")
        else:
            print("NO RESULTS FOUND")
            
        print("\nTesting sort by expiration_date...")
        results2 = await db.get_auctions_with_statistics(
            filters=filters,
            sort_by='expiration_date',
            order='asc',
            limit=50,
            offset=0
        )
        auctions2 = results2.get('auctions', [])
        print(f"Results Count: {len(auctions2)}")
        if auctions2:
            print(f"Top Result: {auctions2[0]['domain']} (Exp: {auctions2[0].get('expiration_date')})")

    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sorting())
