# Troubleshooting Old Reports Not Loading

## Issue
Old reports are not displaying in the reports list, showing timeout errors.

## Root Causes

1. **Missing Fields**: Old reports may not have newer fields like:
   - `backlinks_page_summary`
   - `detailed_data_available`
   - `analysis_phase`
   - `analysis_mode`

2. **Enum Validation**: Status, analysis_phase, and analysis_mode are enums that need proper conversion

3. **Database Migration**: The `backlinks_page_summary` column may not exist if migration hasn't been run

## Fixes Applied

### 1. Backend (`backend/src/api/routes/reports.py`)
- Added proper parsing for all required fields
- Added enum conversion with fallbacks for invalid values
- Added per-report error handling (skips bad reports instead of failing entirely)
- Added detailed error logging

### 2. Database Migration
- Created migration: `backend/supabase/migrations/20250128000000_add_backlinks_page_summary_to_reports.sql`
- **Action Required**: Run this migration on your Supabase database

## Steps to Fix

1. **Run the Migration**:
   ```sql
   ALTER TABLE reports 
   ADD COLUMN IF NOT EXISTS backlinks_page_summary JSONB;
   ```

2. **Check Backend Logs**:
   ```bash
   tail -f backend/backend.log | grep -i "report\|error"
   ```

3. **Test the Endpoint**:
   ```bash
   curl 'http://localhost:8000/api/v1/reports?limit=1'
   ```

4. **Check for Specific Errors**:
   - Look for "Failed to parse report in list" errors
   - Check which domain is failing
   - Verify the error type and message

## Common Issues

### Issue: All reports are skipped
**Solution**: Check logs for validation errors. The error handling now logs:
- Domain name
- Error type
- Error message
- Available keys in the report data

### Issue: Timeout errors
**Solution**: 
- Check if database query is slow
- Verify database connection
- Check if there are too many reports to parse

### Issue: Migration not run
**Solution**: 
- Run the migration SQL on your Supabase database
- The column will be NULL for old reports (which is fine)

## Verification

After applying fixes, old reports should:
1. Load successfully in the reports list
2. Show with default values for missing fields
3. Not cause timeouts or errors

If issues persist, check the backend logs for specific error messages about which reports are failing and why.


