#!/usr/bin/env python3
"""
Test script for auctions system
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.database import get_database, init_database
from services.auctions_service import AuctionsService
from models.auctions import AuctionProcessingConfig

async def test_auctions():
    """Test auctions system"""
    print("=" * 60)
    print("Testing Auctions System")
    print("=" * 60)
    
    # Initialize database first
    print("\n0. Initializing database...")
    try:
        await init_database()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    db = get_database()
    auctions_service = AuctionsService()
    
    # Test 1: Check table exists
    print("\n1. Testing database connection...")
    try:
        result = await db.get_auctions_with_statistics(limit=1, offset=0)
        print("✅ Database connection successful")
        print(f"   Found {result.get('total_count', 0)} auctions in database")
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    
    # Test 2: Test truncate
    print("\n2. Testing truncate...")
    try:
        await db.truncate_auctions()
        print("✅ Truncate successful")
    except Exception as e:
        print(f"❌ Truncate error: {e}")
        return False
    
    # Test 3: Test CSV parsing
    print("\n3. Testing CSV parsing...")
    test_csv = """name,startDate,endDate,price
example.com,2025-01-01T00:00:00Z,2025-12-31T23:59:59Z,100.00
test.com,2025-01-01T00:00:00Z,2025-12-31T23:59:59Z,200.00"""
    
    try:
        auctions = auctions_service.load_auctions_from_csv(test_csv, 'namecheap')
        print(f"✅ CSV parsing successful: {len(auctions)} auctions parsed")
        if auctions:
            print(f"   First auction: {auctions[0].domain} (expires: {auctions[0].expiration_date})")
    except Exception as e:
        print(f"❌ CSV parsing error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Test bulk insert
    print("\n4. Testing bulk insert...")
    try:
        result = await auctions_service.truncate_and_load(auctions)
        print(f"✅ Bulk insert successful: {result['loaded_count']} loaded, {result['skipped_count']} skipped")
    except Exception as e:
        print(f"❌ Bulk insert error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Test processing
    print("\n5. Testing batch processing...")
    try:
        config = AuctionProcessingConfig(
            score_threshold=0.0,  # Accept all
            use_both_thresholds=False,
            batch_size=100
        )
        result = await auctions_service.process_auctions_batch(config)
        print(f"✅ Processing successful: {result['total_processed']} processed, {result['total_preferred']} preferred")
    except Exception as e:
        print(f"❌ Processing error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 6: Test report
    print("\n6. Testing report...")
    try:
        result = await auctions_service.get_auctions_report(limit=10, offset=0)
        print(f"✅ Report successful: {result['count']} auctions returned (total: {result.get('total_count', 0)})")
        if result.get('auctions'):
            auction = result['auctions'][0]
            print(f"   Sample: {auction.get('domain')} - Score: {auction.get('score')}, Preferred: {auction.get('preferred')}")
    except Exception as e:
        print(f"❌ Report error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 7: Test preferred without stats
    print("\n7. Testing preferred auctions query...")
    try:
        preferred = await auctions_service.get_preferred_auctions_without_stats(limit=10)
        print(f"✅ Preferred query successful: {len(preferred)} preferred auctions without statistics")
    except Exception as e:
        print(f"❌ Preferred query error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    return True

if __name__ == '__main__':
    try:
        success = asyncio.run(test_auctions())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)





















