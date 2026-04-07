
import asyncio
import os
import sys
from pathlib import Path
from uuid import UUID

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from services.database import get_database, init_database
from api.routes.analysis import analyze_domain
from models.domain_analysis import DomainAnalysisRequest, AnalysisMode

class MockUser:
    def __init__(self, id, email):
        self.id = UUID(id)
        self.email = email

async def test():
    await init_database()
    
    # Try to analyze a domain
    user = MockUser(id="942d09c0-58ce-4fe5-b412-f16ac1694a72", email="jorge.fernandez@kotechile.cl")
    request = DomainAnalysisRequest(domain="google.com", mode=AnalysisMode.LEGACY)
    
    from fastapi import BackgroundTasks
    bg = BackgroundTasks()
    
    try:
        resp = await analyze_domain(request, bg, user)
        print(f"Success: {resp.success}, Message: {resp.message}")
    except Exception as e:
        print(f"Caught Exception: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
