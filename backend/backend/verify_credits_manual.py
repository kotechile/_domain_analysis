
import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.database import get_database, init_database
from services.credits_service import CreditsService

async def verify_credits_system():
    print("Initializing database...")
    await init_database()
    db = get_database()
    
    if not db.client:
        print("Failed to initialize database client. Check your .env file.")
        return

    print("--- Verifying Credits System ---")
    
    # 1. Check if tables exist (by trying to query)
    try:
        print("Checking tables...")
        db.client.table('user_credits').select('*').limit(1).execute()
        print("✅ Table 'user_credits' exists.")
    except Exception as e:
        print(f"❌ Table 'user_credits' does NOT exist. Error: {e}")
        print("Did you run 'backend/credits_migration.sql' in Supabase SQL Editor?")
        return

    # 2. Get a test user (your own user or first user in auth.users if accessible, 
    # but we can't query auth.users easily. logic below assumes we want to test with a specific user)
    # For manual verification, let's create a dummy user ID or ask user to provide one.
    # Since we can't interact, let's just use a hardcoded UUID or try to find one from reports.
    
    user_id = "00000000-0000-0000-0000-000000000000" # Dummy ID
    
    credits_service = CreditsService(db)
    
    # 3. Check Initial Balance
    balance = await credits_service.get_balance(user_id)
    print(f"Current Balance for {user_id}: ${balance}")
    
    # 4. Add Credits
    print("Adding $10.00 credits...")
    new_balance = await credits_service.add_credits(user_id, 10.00, "Test Purchase", "test_ref_1")
    print(f"New Balance: ${new_balance}")
    
    if new_balance == balance + 10.00:
        print("✅ Add Credits: Success")
    else:
        print("❌ Add Credits: Failed (Balance mismatch)")
        
    # 5. Deduct Credits
    print("Deducting $2.50 credits...")
    success = await credits_service.deduct_credits(user_id, 2.50, "Test Usage", "test_ref_2")
    if success:
        print("✅ Deduct Credits: Success")
        final_balance = await credits_service.get_balance(user_id)
        print(f"Final Balance: ${final_balance}")
        
        if abs(final_balance - (new_balance - 2.50)) < 0.0001:
             print("✅ Balance Calculation: Correct")
        else:
             print("❌ Balance Calculation: Incorrect")
    else:
        print("❌ Deduct Credits: Failed")
        
    print("--- Verification Complete ---")

if __name__ == "__main__":
    asyncio.run(verify_credits_system())
