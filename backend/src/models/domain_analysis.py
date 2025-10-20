"""
Domain analysis data models
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class AnalysisStatus(str, Enum):
    """Status of domain analysis"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class DataSource(str, Enum):
    """External data sources"""
    DATAFORSEO = "dataforseo"
    WAYBACK_MACHINE = "wayback_machine"
    GEMINI = "gemini"


class DomainAnalysisRequest(BaseModel):
    """Request model for domain analysis"""
    domain: str = Field(..., min_length=3, max_length=255, description="Domain to analyze")
    
    @validator('domain')
    def validate_domain(cls, v):
        """Validate domain format"""
        if not v or '.' not in v:
            raise ValueError('Invalid domain format')
        # Remove protocol if present
        v = v.replace('http://', '').replace('https://', '').replace('www.', '')
        return v.lower().strip()


class DataForSEOMetrics(BaseModel):
    """DataForSEO metrics model"""
    domain_rating_dr: Optional[float] = Field(None, ge=0, le=100)
    organic_traffic_est: Optional[int] = Field(None, ge=0)
    total_referring_domains: Optional[int] = Field(None, ge=0)
    total_backlinks: Optional[int] = Field(None, ge=0)
    referring_domains_info: Optional[List[Dict[str, Any]]] = None
    organic_keywords: Optional[List[Dict[str, Any]]] = None


class WaybackMachineSummary(BaseModel):
    """Wayback Machine data summary"""
    first_capture_year: Optional[int] = None
    total_captures: Optional[int] = Field(None, ge=0)
    last_capture_date: Optional[datetime] = None
    historical_risk_assessment: Optional[str] = None
    earliest_snapshot_url: Optional[str] = None


class LLMAnalysis(BaseModel):
    """LLM-generated analysis results"""
    good_highlights: List[str] = Field(default_factory=list, max_items=5)
    bad_highlights: List[str] = Field(default_factory=list, max_items=5)
    suggested_niches: List[str] = Field(default_factory=list, max_items=5)
    advantages_disadvantages_table: List[Dict[str, str]] = Field(default_factory=list)
    summary: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=1)


class DomainAnalysisReport(BaseModel):
    """Complete domain analysis report"""
    domain_name: str
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: AnalysisStatus = AnalysisStatus.PENDING
    data_for_seo_metrics: Optional[DataForSEOMetrics] = None
    wayback_machine_summary: Optional[WaybackMachineSummary] = None
    llm_analysis: Optional[LLMAnalysis] = None
    raw_data_links: Optional[Dict[str, str]] = None
    processing_time_seconds: Optional[float] = None
    error_message: Optional[str] = None


class RawDataCache(BaseModel):
    """Raw data cache model"""
    domain_name: str
    api_source: DataSource
    json_data: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class AnalysisResponse(BaseModel):
    """API response model for analysis requests"""
    success: bool
    message: str
    report_id: Optional[str] = None
    estimated_completion_time: Optional[int] = None  # seconds


class ReportResponse(BaseModel):
    """API response model for report retrieval"""
    success: bool
    report: Optional[DomainAnalysisReport] = None
    message: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    services: Dict[str, str] = Field(default_factory=dict)
