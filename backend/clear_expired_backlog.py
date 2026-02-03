import asyncio
from datetime import datetime, timezone
from src.services.database import init_database, get_database

async def clear_backlog():
    await init_database()
    db = get_database()
    
    now_ts = datetime.now(timezone.utc).isoformat()
    total_deleted = 0
    
    print(f"Starting backlog cleanup for auctions expired before {now_ts}...")
    
    while True:
        try:
            # We fetch up to 1000 IDs to delete in this batch
            # Direct DELETE with where clause and limit isn't supported in Supabase REST API directly for bulk
            # but we can do it via a subquery or just repeat the RPC if the RPC has the limit.
            
            # Since the RPC 'delete_expired_auctions' has the limit of 10000, we'll just call it repeatedly!
            res = db.client.rpc('delete_expired_auctions', {}).execute()
            count = res.data if res.data is not None else 0
            
            if count == 0:
                print("No more expired auctions to delete.")
                break
                
            total_deleted += count
            print(f"Deleted {count} auctions... Total deleted so far: {total_deleted}")
            
            # Small sleep to avoid hammering the DB too hard
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"Error during cleanup batch: {e}")
            break
            
    print(f"\nCleanup finished! Total auctions cleared: {total_deleted}")

if __name__ == "__main__":
    asyncio.run(clear_backlog())
