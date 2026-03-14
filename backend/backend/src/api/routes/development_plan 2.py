from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any
import structlog

from services.database import DatabaseService
from services.external_apis import LLMService

logger = structlog.get_logger()

router = APIRouter()

class DevelopmentPlanRequest(BaseModel):
    domain: str

class DevelopmentPlanResponse(BaseModel):
    success: bool
    plan: Dict[str, Any]
    message: str

@router.post("/development-plan", response_model=DevelopmentPlanResponse)
async def generate_development_plan(
    request: DevelopmentPlanRequest,
    db: DatabaseService = Depends()
):
    """
    Generate a development plan for a domain based on its analysis data.
    """
    try:
        domain = request.domain.lower().strip()
        logger.info("Generating development plan", domain=domain)
        
        # Get the latest report for the domain
        report = await db.get_report(domain)
        if not report:
            raise HTTPException(
                status_code=404, 
                detail=f"No analysis report found for domain: {domain}"
            )
        
        if report.status != 'completed':
            raise HTTPException(
                status_code=400,
                detail=f"Analysis not completed for domain: {domain}. Status: {report.status}"
            )
        
        # Initialize LLM service
        llm_service = LLMService()
        
        # Generate development plan using LLM
        development_plan = await llm_service.generate_development_plan(report)
        
        logger.info("Development plan generated successfully", domain=domain)
        
        return DevelopmentPlanResponse(
            success=True,
            plan=development_plan,
            message="Development plan generated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate development plan", domain=domain, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate development plan: {str(e)}"
        )
