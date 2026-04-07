import asyncio
from src.services.database import DatabaseService

async def check_counts():
    db = DatabaseService()
    client = await db._get_client()
    
    # Check total counts
    total = await client.table('auctions').select('id', count='exact').execute()
    processed = await client.table('auctions').select('id', count='exact').eq('processed', True).execute()
    has_stats = await client.table('auctions').select('id', count='exact').eq('has_statistics', True).execute()
    has_dr = await client.table('auctions').select('id', count='exact').not_.is_('domain_rating', 'null').execute()
    has_score = await client.table('auctions').select('id', count='exact').not_.is_('score', 'null').execute()
    preferred = await client.table('auctions').select('id', count='exact').eq('preferred', True).execute()
    to_delete = await client.table('auctions').select('id', count='exact').eq('to_delete', True).execute()

    print(f"Total: {total.count}")
    print(f"Processed: {processed.count}")
    print(f"Has Statistics: {has_stats.count}")
    print(f"Has Domain Rating: {has_dr.count}")
    print(f"Has Score: {has_score.count}")
    print(f"Preferred: {preferred.count}")
    print(f"To Delete: {to_delete.count}")

    # Check some samples if has_dr > 0
    if has_dr.count > 0:
        samples = await client.table('auctions').select('domain', 'domain_rating', 'score').not_.is_('domain_rating', 'null').limit(5).execute()
        print("\nSamples with DR:")
        for s in samples.data:
            print(s)

if __name__ == "__main__":
    asyncio.run(check_counts())
