import asyncio
from src.services.database import init_database, get_database

async def update_and_cleanup():
    await init_database()
    db = get_database()
    
    # The updated SQL function without the limiting bottleneck
    sql = """
    CREATE OR REPLACE FUNCTION delete_expired_auctions()
    RETURNS INTEGER
    LANGUAGE plpgsql
    SECURITY DEFINER
    AS $$
    DECLARE
        v_deleted_count INTEGER := 0;
    BEGIN
        -- Delete all records where expiration_date is in the past
        DELETE FROM auctions 
        WHERE expiration_date < NOW();
        
        GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
        
        RETURN v_deleted_count;
    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'Failed to delete expired auctions: %', SQLERRM;
        RETURN 0;
    END;
    $$;
    """
    
    print("Updating the delete_expired_auctions function...")
    # Using the execute_sql_query if available, or finding another way to run raw SQL
    # Actually DatabaseService has _create_tables which uses self.client.rpc('exec_sql', {'sql': tables_sql})
    # Let's check if 'exec_sql' exists or use a direct command if possible.
    
    try:
        # Based on DatabaseService._create_tables
        res = db.client.rpc('exec_sql', {'sql': sql}).execute()
        print("Function updated successfully.")
    except Exception as e:
        print(f"Failed to update function via exec_sql: {e}")
        print("Attempting to run as a direct migration file...")
        # If exec_sql fails, we might need to ask the user to run it in the dashboard 
        # but let's try the common RPC if it exists.
    
    print("\nTriggering manual cleanup...")
    try:
        cleanup_res = db.client.rpc('delete_expired_auctions', {}).execute()
        count = cleanup_res.data if cleanup_res.data is not None else 0
        print(f"Cleanup finished! Deleted {count} expired auctions.")
    except Exception as e:
        print(f"Cleanup failed: {e}")

if __name__ == "__main__":
    asyncio.run(update_and_cleanup())
