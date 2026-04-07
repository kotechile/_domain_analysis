
import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.database import init_database, get_database

async def run():
    await init_database()
    db = get_database()
    client = await db._get_client()
    
    # Try to find users in user_credits
    res = await client.table('user_credits').select('*').execute()
    print("User credits found:", res.data)
    
    if not res.data:
        print("No user credits found. Checking for any users at all...")
        # Since I can't find a good public user table, I'll check 'reports' or something to see if there are user_ids
        rep_res = await client.table('reports').select('user_id').limit(1).execute()
        if rep_res.data:
            user_id = rep_res.data[0]['user_id']
            print(f"Found a user_id {user_id} in reports table. Granting credits...")
            await client.table('user_credits').upsert({
                'user_id': user_id,
                'balance': 100000,
                'total_purchased': 100000,
                'updated_at': 'now()'
            }).execute()
        else:
            print("No user_id found in reports either.")
        return

    # Grant 100,000 credits to each found user
    for entry in res.data:
        user_id = entry['user_id']
        await client.table('user_credits').update({
            'balance': 100000,
            'updated_at': 'now()'
        }).eq('user_id', user_id).execute()
        print(f"Updated credits for {user_id} to 100,000")

if __name__ == "__main__":
    asyncio.run(run())
