import asyncio
import os
from src.services.database import DatabaseService

async def inspect():
    # Initialize database
    db = DatabaseService.initialize()
    
    # Find records with statistics
    result = db.client.table('auctions').select('domain, page_statistics, organic_traffic, domain_rating').eq('has_statistics', True).limit(5).execute()
    
    if not result.data:
        print("No records found with has_statistics=True")
        return
        
    for row in result.data:
        print(f"Domain: {row['domain']}")
        print(f"Organic Traffic column: {row['organic_traffic']}")
        print(f"Domain Rating column: {row['domain_rating']}")
        print(f"Page Statistics: {row['page_statistics']}")
        print("-" * 20)

if __name__ == "__main__":
    asyncio.run(inspect())
