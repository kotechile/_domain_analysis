import asyncio
import os
import sys
from dotenv import load_dotenv

# Setup paths and env
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
load_dotenv(os.path.join(os.path.dirname(__file__), 'src/.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from services.database import get_database, init_database
from services.csv_parser_service import CSVParserService
import structlog

import logging

# Configure basic logging to stdout
logging.basicConfig(level=logging.INFO)
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

async def debug_namesilo():
    print("Initializing...")
    await init_database()
    db = get_database()
    
    bucket = "auction-csvs"
    filename = "namesilo_export.csv"
    local_path = "temp_debug_namesilo.csv"
    
    print(f"Downloading {filename} from {bucket}...")
    try:
        await db.download_to_file(bucket, filename, local_path)
        print("Download successful.")
    except Exception as e:
        print(f"Download failed: {e}")
        return

    print("Parsing file...")
    parser = CSVParserService()
    
    try:
        auctions = parser.parse_csv(local_path, "namesilo", is_file=True)
        print(f"Success! Parsed {len(auctions)} auctions.")
        if auctions:
            print("First 3 auctions:")
            for a in auctions[:3]:
                print(f"  - Domain: {a.domain}, Price: {a.current_bid}, Link: {a.link}")
    except Exception as e:
        print(f"Parsing FAILED as expected. Error details:")
        print("-" * 60)
        print(str(e))
        print("-" * 60)
    
    # Clean up
    if os.path.exists(local_path):
        os.remove(local_path)
        print("Cleaned up temp file.")

if __name__ == "__main__":
    asyncio.run(debug_namesilo())
