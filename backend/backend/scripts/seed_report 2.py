
import asyncio
import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from services.database import init_database, get_database
from models.domain_analysis import DomainAnalysisReport, AnalysisStatus, AnalysisPhase, AnalysisMode

async def seed():
    print("Initializing database connection...")
    await init_database()
    db = get_database()
    
    domain = "webflow.com"
    print(f"Seeding report for {domain}...")
    
    report = DomainAnalysisReport(
        domain_name=domain,
        status=AnalysisStatus.PENDING,
        analysis_phase=AnalysisPhase.DETAILED,
        analysis_mode=AnalysisMode.LEGACY
    )
    
    # We can use upsert to ensure it exists
    await db.save_report(report)
    print(f"✅ Seeded report for {domain}")

if __name__ == "__main__":
    asyncio.run(seed())
