import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))
from services.database import DatabaseService

async def check_constraints():
    db = DatabaseService()
    # Note: exec_sql failed earlier, maybe it wasn't created.
    # I'll try to find it via direct query if I can, but Supabase client is limited.
    # I'll just check what happens if I try to upsert a dummy GoDaddy record.
    
    try:
        dummy = {
            'domain': 'dummy-godaddy-upsert.com',
            'auction_site': 'godaddy',
            'expiration_date': '2025-12-31T23:59:59+00:00',
            'processed': True,
            'offer_type': 'auction'
        }
        res = db.client.table('auctions').upsert(dummy, on_conflict='domain,auction_site,expiration_date').execute()
        print("✅ Successfully upserted dummy GoDaddy record.")
        db.client.table('auctions').delete().eq('domain', 'dummy-godaddy-upsert.com').execute()
    except Exception as e:
        print(f"❌ Failed to upsert dummy record: {e}")

if __name__ == "__main__":
    asyncio.run(check_constraints())
