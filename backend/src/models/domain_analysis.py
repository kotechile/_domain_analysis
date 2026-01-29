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


class AnalysisPhase(str, Enum):
    """Analysis phase for progress tracking"""
    ESSENTIAL = "essential"
    DETAILED = "detailed"
    AI_ANALYSIS = "ai_analysis"
    COMPLETED = "completed"


class AnalysisMode(str, Enum):
    """Analysis mode for dual-mode operation"""
    LEGACY = "legacy"
    ASYNC = "async"
    DUAL = "dual"


class DetailedDataType(str, Enum):
    """Types of detailed analysis data"""
    BACKLINKS = "backlinks"
    KEYWORDS = "keywords"
    REFERRING_DOMAINS = "referring_domains"


class AsyncTaskStatus(str, Enum):
    """Status of async tasks"""
    PENDING = "pending"
    PROCESSING = "processing"
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


class OrganicMetrics(BaseModel):
    """Organic search metrics from domain rank overview"""
    pos_1: int = 0
    pos_2_3: int = 0
    pos_4_10: int = 0
    pos_11_20: int = 0
    pos_21_30: int = 0
    pos_31_40: int = 0
    pos_41_50: int = 0
    pos_51_60: int = 0
    pos_61_70: int = 0
    pos_71_80: int = 0
    pos_81_90: int = 0
    pos_91_100: int = 0
    etv: float = 0.0
    count: int = 0
    estimated_paid_traffic_cost: float = 0.0
    is_new: int = 0
    is_up: int = 0
    is_down: int = 0
    is_lost: int = 0


class PaidMetrics(BaseModel):
    """Paid search metrics from domain rank overview"""
    pos_1: int = 0
    pos_2_3: int = 0
    pos_4_10: int = 0
    pos_11_20: int = 0
    pos_21_30: int = 0
    pos_31_40: int = 0
    pos_41_50: int = 0
    pos_51_60: int = 0
    pos_61_70: int = 0
    pos_71_80: int = 0
    pos_81_90: int = 0
    pos_91_100: int = 0
    etv: float = 0.0
    count: int = 0
    estimated_paid_traffic_cost: float = 0.0
    is_new: int = 0
    is_up: int = 0
    is_down: int = 0
    is_lost: int = 0


class DataForSEOMetrics(BaseModel):
    """DataForSEO metrics model"""
    domain_rating_dr: Optional[float] = Field(None, ge=0, le=100, description="DataForSEO Rank (PageRank-like metric, 0-100 scale)")
    organic_traffic_est: Optional[float] = Field(None, ge=0)
    total_referring_domains: Optional[int] = Field(None, ge=0)
    total_backlinks: Optional[int] = Field(None, ge=0)
    referring_domains_info: Optional[List[Dict[str, Any]]] = None
    organic_keywords: Optional[List[Dict[str, Any]]] = None
    # Domain rank overview data
    total_keywords: Optional[int] = Field(None, ge=0)
    organic_metrics: Optional[OrganicMetrics] = None
    paid_metrics: Optional[PaidMetrics] = None


class WaybackMachineSummary(BaseModel):
    """Wayback Machine data summary"""
    first_capture_year: Optional[int] = None
    total_captures: Optional[int] = Field(None, ge=0)
    last_capture_date: Optional[datetime] = None
    historical_risk_assessment: Optional[str] = None
    earliest_snapshot_url: Optional[str] = None


class LLMAnalysis(BaseModel):
    """LLM-generated analysis results"""
    # Legacy fields (kept for backward compatibility)
    good_highlights: List[str] = Field(default_factory=list, max_items=5)
    bad_highlights: List[str] = Field(default_factory=list, max_items=5)
    suggested_niches: List[str] = Field(default_factory=list, max_items=5)
    advantages_disadvantages_table: List[Dict[str, str]] = Field(default_factory=list)
    
    # Enhanced domain buyer-focused fields
    buy_recommendation: Optional[Dict[str, Any]] = None
    valuable_assets: List[str] = Field(default_factory=list)
    major_concerns: List[str] = Field(default_factory=list)
    content_strategy: Optional[Dict[str, Any]] = None
    action_plan: Optional[Dict[str, Any]] = None
    pros_and_cons: List[Dict[str, str]] = Field(default_factory=list)
    
    # Common fields
    summary: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=1)


class HistoricalMetricPoint(BaseModel):
    """Data point for historical metrics"""
    date: str  # YYYY-MM-DD
    value: float


class HistoricalRankOverview(BaseModel):
    """Historical ranking overview data"""
    organic_keywords_count: List[HistoricalMetricPoint] = []
    organic_traffic: List[HistoricalMetricPoint] = []
    organic_traffic_value: List[HistoricalMetricPoint] = []
    raw_items: Optional[List[Dict[str, Any]]] = None


class TrafficAnalyticsHistory(BaseModel):
    """Historical traffic analytics data"""
    visits_history: List[HistoricalMetricPoint] = []
    bounce_rate_history: List[HistoricalMetricPoint] = []
    unique_visitors_history: List[HistoricalMetricPoint] = []
    raw_items: Optional[List[Dict[str, Any]]] = None


class HistoricalData(BaseModel):
    """Combined historical data container"""
    rank_overview: Optional[HistoricalRankOverview] = None
    traffic_analytics: Optional[TrafficAnalyticsHistory] = None
    backlinks_history: Optional[Dict[str, List[HistoricalMetricPoint]]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class DetailedAnalysisData(BaseModel):
    """Detailed analysis data storage model"""
    id: Optional[str] = None
    domain_name: str
    data_type: DetailedDataType
    json_data: Dict[str, Any]
    task_id: Optional[str] = None
    data_source: str = "dataforseo"
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class AsyncTask(BaseModel):
    """Async task tracking model"""
    id: Optional[str] = None
    domain_name: str
    task_id: str
    task_type: DetailedDataType
    status: AsyncTaskStatus = AsyncTaskStatus.PENDING
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class AnalysisModeConfig(BaseModel):
    """Analysis mode configuration model"""
    id: Optional[str] = None
    domain_name: Optional[str] = None
    mode_preference: AnalysisMode = AnalysisMode.DUAL
    async_enabled: bool = True
    cache_ttl_hours: int = 24
    manual_refresh_enabled: bool = True
    progress_indicators_enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProgressInfo(BaseModel):
    """Progress tracking information"""
    status: AsyncTaskStatus
    phase: AnalysisPhase
    progress_percentage: int = Field(ge=0, le=100)
    estimated_time_remaining: Optional[int] = None
    current_operation: Optional[str] = None
    completed_operations: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


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
    # Enhanced fields for dual-mode operation
    detailed_data_available: Dict[str, bool] = Field(default_factory=dict)
    analysis_phase: AnalysisPhase = AnalysisPhase.ESSENTIAL
    analysis_mode: AnalysisMode = AnalysisMode.LEGACY
    progress_data: Optional[ProgressInfo] = None
    # Backlinks page summary (from DataForSEO backlinks summary endpoint)
    # Using forward reference since BulkPageSummaryResult is defined later
    backlinks_page_summary: Optional['BulkPageSummaryResult'] = None
    historical_data: Optional['HistoricalData'] = None
    
    class Config:
        """Pydantic config for forward references"""
        arbitrary_types_allowed = True


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


# Bulk Domain Analysis Models

class BulkPageSummaryInfo(BaseModel):
    """Info object from DataForSeo bulk pages summary"""
    server: Optional[str] = None
    cms: Optional[str] = None
    platform_type: Optional[List[str]] = None
    ip_address: Optional[str] = None
    country: Optional[str] = None
    is_ip: Optional[bool] = None
    target_spam_score: Optional[int] = None


class BulkPageSummaryResult(BaseModel):
    """Complete result object from DataForSeo bulk_pages_summary endpoint"""
    target: Optional[str] = Field(default=None, description="Target domain (optional for backlinks_summary compatibility)")
    first_seen: Optional[str] = None
    lost_date: Optional[str] = None
    rank: Optional[int] = None
    backlinks: Optional[int] = None
    backlinks_spam_score: Optional[int] = None
    crawled_pages: Optional[int] = None
    info: Optional[BulkPageSummaryInfo] = None
    internal_links_count: Optional[int] = None
    external_links_count: Optional[int] = None
    broken_backlinks: Optional[int] = None
    broken_pages: Optional[int] = None
    referring_domains: Optional[int] = None
    referring_domains_nofollow: Optional[int] = None
    referring_main_domains: Optional[int] = None
    referring_main_domains_nofollow: Optional[int] = None
    referring_ips: Optional[int] = None
    referring_subnets: Optional[int] = None
    referring_pages: Optional[int] = None
    referring_pages_nofollow: Optional[int] = None
    referring_links_tld: Optional[Dict[str, int]] = None
    referring_links_types: Optional[Dict[str, int]] = None
    referring_links_attributes: Optional[Dict[str, int]] = None
    referring_links_platform_types: Optional[Dict[str, int]] = None
    referring_links_countries: Optional[Dict[str, int]] = None
    referring_links_semantic_locations: Optional[Dict[str, int]] = None


class BulkDomainInput(BaseModel):
    """Input model for parsing domain list file"""
    domain: str
    provider: Optional[str] = None
    
    @validator('domain')
    def validate_domain(cls, v):
        """Validate domain format"""
        if not v or '.' not in v:
            raise ValueError('Invalid domain format')
        # Remove protocol if present
        v = v.replace('http://', '').replace('https://', '').replace('www.', '')
        return v.lower().strip()


class BulkDomainAnalysis(BaseModel):
    """Database model for bulk domain analysis records"""
    id: Optional[str] = None
    domain_name: str
    provider: Optional[str] = None
    backlinks_bulk_page_summary: Optional[BulkPageSummaryResult] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BulkDomainSyncResult(BaseModel):
    """Response model for bulk domain sync operations"""
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    total_count: int = 0
    created_domains: List[str] = Field(default_factory=list)
    updated_domains: List[str] = Field(default_factory=list)
    skipped_domains: List[str] = Field(default_factory=list)


# Namecheap Domain Models

class NamecheapDomain(BaseModel):
    """Model for Namecheap auction domain data"""
    id: Optional[str] = None
    url: Optional[str] = None
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    price: Optional[float] = None
    start_price: Optional[float] = None
    renew_price: Optional[float] = None
    bid_count: Optional[int] = None
    ahrefs_domain_rating: Optional[float] = None
    umbrella_ranking: Optional[int] = None
    cloudflare_ranking: Optional[int] = None
    estibot_value: Optional[float] = None
    extensions_taken: Optional[int] = None
    keyword_search_count: Optional[int] = None
    registered_date: Optional[datetime] = None
    last_sold_price: Optional[float] = None
    last_sold_year: Optional[int] = None
    is_partner_sale: Optional[bool] = None
    semrush_a_score: Optional[int] = None
    majestic_citation: Optional[int] = None
    ahrefs_backlinks: Optional[int] = None
    semrush_backlinks: Optional[int] = None
    majestic_backlinks: Optional[int] = None
    majestic_trust_flow: Optional[float] = None
    go_value: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class NamecheapDomainListResponse(BaseModel):
    """Response model for listing Namecheap domains"""
    success: bool
    count: int
    domains: List[NamecheapDomain]
    total_count: Optional[int] = None
    has_more: Optional[bool] = None
    
    class Config:
        extra = "allow"  # Allow extra fields like scoring_stats


class NamecheapDomainSelection(BaseModel):
    """Model for selected domains for analysis"""
    domain_names: List[str] = Field(..., min_items=1)


class NamecheapAnalysisResult(BaseModel):
    """Combined result for Namecheap domain with DataForSeo analysis"""
    domain: str
    namecheap_data: Optional[NamecheapDomain] = None
    dataforseo_data: Optional[BulkPageSummaryResult] = None
    has_data: bool = False
    status: str = "pending"  # pending, has_data, triggered, error
    error: Optional[str] = None


class NamecheapAnalysisResponse(BaseModel):
    """Response model for bulk analysis of selected domains"""
    success: bool
    results: List[NamecheapAnalysisResult]
    total_selected: int
    has_data_count: int = 0
    triggered_count: int = 0
    error_count: int = 0


class ScoredDomain(BaseModel):
    """Model for domain scoring results (in-memory only)"""
    domain: NamecheapDomain
    filter_status: str  # 'PASS' or 'FAIL'
    filter_reason: Optional[str] = None
    total_meaning_score: Optional[float] = None  # 0-100
    age_score: Optional[float] = None
    lexical_frequency_score: Optional[float] = None
    semantic_value_score: Optional[float] = None
    rank: Optional[int] = None  # Position in ranked list


class HistoricalMetricPoint(BaseModel):
    """Single data point for historical metrics"""
    date: datetime
    value: float
    
    @validator('date', pre=True)
    def parse_date(cls, v):
        if isinstance(v, str):
            try:
                # Handle YYYY-MM-DD format
                return datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                try:
                    # Handle YYYY-MM-DDTHH:MM:SS format
                    return datetime.fromisoformat(v.replace('Z', '+00:00'))
                except ValueError:
                    return v
        return v


class HistoricalRankOverview(BaseModel):
    """Historical rank overview data"""
    organic_keywords_count: List[HistoricalMetricPoint] = Field(default_factory=list)
    organic_traffic: List[HistoricalMetricPoint] = Field(default_factory=list)
    organic_traffic_value: List[HistoricalMetricPoint] = Field(default_factory=list)
    
    # Store raw items for flexible charting if needed
    raw_items: Optional[List[Dict[str, Any]]] = None


class TrafficAnalyticsHistory(BaseModel):
    """Traffic analytics history data"""
    visits_history: List[HistoricalMetricPoint] = Field(default_factory=list)
    bounce_rate_history: List[HistoricalMetricPoint] = Field(default_factory=list)
    unique_visitors_history: List[HistoricalMetricPoint] = Field(default_factory=list)
    
    # Store raw items
    raw_items: Optional[List[Dict[str, Any]]] = None


class HistoricalData(BaseModel):
    """Container for all historical data"""
    rank_overview: Optional[HistoricalRankOverview] = None
    traffic_analytics: Optional[TrafficAnalyticsHistory] = None
    backlinks_history: Optional[Dict[str, List[HistoricalMetricPoint]]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

