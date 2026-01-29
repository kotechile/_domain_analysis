# Auctions System Testing Guide

## Quick Test Checklist

- [ ] Database migration applied successfully
- [ ] Backend server starts without errors
- [ ] Frontend page loads
- [ ] CSV upload works
- [ ] Processing works
- [ ] Report displays correctly

## 1. Verify Database Migration

### Check Table Exists
```sql
-- Run in Supabase Studio SQL Editor
SELECT * FROM auctions LIMIT 1;
```

Should return an empty result (no error = table exists).

### Check Table Structure
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'auctions'
ORDER BY ordinal_position;
```

Should show all columns: id, domain, start_date, expiration_date, auction_site, ranking, score, preferred, has_statistics, source_data, created_at, updated_at.

### Check Indexes
```sql
SELECT indexname FROM pg_indexes WHERE tablename = 'auctions';
```

Should show 7 indexes.

## 2. Test Backend API

### Start Backend Server
```bash
cd backend
source venv/bin/activate  # or your virtual environment
python run_server.py
```

Server should start on `http://localhost:8000` without errors.

### Test Health Endpoint
```bash
curl http://localhost:8000/api/v1/health
```

Should return: `{"status": "healthy"}`

### Test Auctions Endpoints

#### 1. Upload CSV (Test with sample data)
```bash
# Create a test CSV file
cat > /tmp/test_auctions.csv << 'EOF'
name,startDate,endDate,price
example.com,2025-01-01T00:00:00Z,2025-12-31T23:59:59Z,100.00
test.com,2025-01-01T00:00:00Z,2025-12-31T23:59:59Z,200.00
EOF

# Upload via API
curl -X POST "http://localhost:8000/api/v1/auctions/upload-csv?auction_site=namecheap" \
  -F "file=@/tmp/test_auctions.csv"
```

Expected response:
```json
{
  "success": true,
  "message": "Loaded 2 auctions, skipped 0 duplicates",
  "loaded_count": 2,
  "skipped_count": 0,
  "total_count": 2
}
```

#### 2. Process Auctions
```bash
curl -X POST "http://localhost:8000/api/v1/auctions/process" \
  -H "Content-Type: application/json" \
  -d '{
    "score_threshold": 50.0,
    "rank_threshold": 1000,
    "use_both_thresholds": false,
    "batch_size": 10000
  }'
```

Expected response:
```json
{
  "success": true,
  "total_processed": 2,
  "total_preferred": 2,
  "message": "Processed 2 auctions, 2 marked as preferred"
}
```

#### 3. Get Report
```bash
curl "http://localhost:8000/api/v1/auctions/report?limit=10&offset=0"
```

Should return auctions with their data.

#### 4. Trigger Analysis (Optional - requires N8N setup)
```bash
curl -X POST "http://localhost:8000/api/v1/auctions/trigger-analysis?limit=1000"
```

## 3. Test Frontend

### Start Frontend
```bash
cd frontend
npm start
```

Frontend should start on `http://localhost:3010`

### Test Steps:

1. **Navigate to Auctions Page**
   - Go to `http://localhost:3010/auctions`
   - Page should load without errors
   - You should see 4 sections:
     - Upload CSV File
     - Process Auctions
     - Trigger DataForSEO Analysis
     - Auctions Report

2. **Test CSV Upload**
   - Click "Select CSV File"
   - Choose a CSV file (use your actual Namecheap export or test file)
   - Select auction site (Namecheap, GoDaddy, or NameSilo)
   - Click "Upload"
   - Should see success message with loaded count

3. **Test Processing**
   - Set score threshold (e.g., 50.0)
   - Set rank threshold (e.g., 1000)
   - Choose threshold logic (either/both)
   - Click "Process Auctions"
   - Should see processing progress and success message

4. **Test Report**
   - Report table should appear below
   - Try filtering by "Preferred Only"
   - Try filtering by auction site
   - Try sorting by different columns
   - Check pagination works

5. **Test Trigger Analysis** (if N8N is configured)
   - Click "Trigger DataForSEO Analysis"
   - Should see success message with triggered count

## 4. Python Test Script

Create a comprehensive test script:

```python
# backend/test_auctions.py
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.database import get_database
from services.auctions_service import AuctionsService
from models.auctions import AuctionProcessingConfig

async def test_auctions():
    """Test auctions system"""
    print("=" * 60)
    print("Testing Auctions System")
    print("=" * 60)
    
    db = get_database()
    auctions_service = AuctionsService()
    
    # Test 1: Check table exists
    print("\n1. Testing database connection...")
    try:
        result = await db.get_auctions_with_statistics(limit=1, offset=0)
        print("✅ Database connection successful")
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
    except Exception as e:
        print(f"❌ CSV parsing error: {e}")
        return False
    
    # Test 4: Test bulk insert
    print("\n4. Testing bulk insert...")
    try:
        result = await auctions_service.truncate_and_load(auctions)
        print(f"✅ Bulk insert successful: {result['loaded_count']} loaded")
    except Exception as e:
        print(f"❌ Bulk insert error: {e}")
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
        return False
    
    # Test 6: Test report
    print("\n6. Testing report...")
    try:
        result = await auctions_service.get_auctions_report(limit=10, offset=0)
        print(f"✅ Report successful: {result['count']} auctions returned")
    except Exception as e:
        print(f"❌ Report error: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = asyncio.run(test_auctions())
    sys.exit(0 if success else 1)
```

Run it:
```bash
cd backend
source venv/bin/activate
python test_auctions.py
```

## 5. End-to-End Workflow Test

### Complete Workflow:

1. **Upload CSV**
   - Use a real Namecheap CSV export
   - Should load all domains into auctions table

2. **Process All**
   - Set thresholds (e.g., score >= 50 OR rank <= 1000)
   - Process all auctions
   - Check that preferred domains are marked

3. **View Report**
   - Filter by preferred
   - Sort by expiration_date
   - Verify statistics show NULL for domains without data

4. **Trigger Analysis** (if N8N configured)
   - Trigger for top 1000 preferred domains
   - Wait for N8N to process
   - Check that has_statistics flag updates

## 6. Common Issues & Solutions

### Issue: "Table does not exist"
**Solution:** Migration not applied. Re-run migration.

### Issue: "Function update_updated_at_column() does not exist"
**Solution:** Run the base tables migration first:
```sql
-- From supabase/migrations/20251022153242_create_base_tables.sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';
```

### Issue: Backend won't start
**Solution:** Check imports:
```bash
cd backend
python -c "from src.services.auctions_service import AuctionsService; print('OK')"
```

### Issue: Frontend shows errors
**Solution:** Check browser console for errors. Verify API URL in `.env`:
```
REACT_APP_API_URL=http://localhost:8000/api/v1
```

## 7. Performance Testing

For large datasets (900K+ records):

1. **Upload Test**
   - Upload large CSV (100K+ records)
   - Monitor memory usage
   - Should complete without OOM errors

2. **Processing Test**
   - Process in batches
   - Monitor progress
   - Should complete in reasonable time

3. **Report Test**
   - Load report with pagination
   - Test sorting and filtering
   - Should be responsive

## Next Steps

After successful testing:
1. Upload your real CSV files
2. Process with your preferred thresholds
3. Trigger DataForSEO analysis for preferred domains
4. Monitor the report for new statistics





















