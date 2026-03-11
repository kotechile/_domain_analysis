// API Response Types
export interface AnalysisResponse {
    success: boolean;
    message: string;
    report_id?: string;
    estimated_completion_time?: number;
}

export interface ReportResponse {
    success: boolean;
    report?: DomainAnalysisReport;
    message?: string;
}

export interface ProgressResponse {
    success: boolean;
    message: string;
    progress?: ProgressInfo;
}

export interface ProgressInfo {
    domain: string;
    status: string;
    phase: string;
    progress_percentage: number;
    current_operation: string;
    status_message: string;
    completed_operations: number;
    total_operations: number;
    estimated_time_remaining: number;
    detailed_status: string[];
    last_updated: string;
}

export interface HistoricalMetricPoint {
    date: string;
    value: number;
}

export interface HistoricalRankOverview {
    organic_keywords_count: HistoricalMetricPoint[];
    organic_traffic: HistoricalMetricPoint[];
    organic_traffic_value: HistoricalMetricPoint[];
    raw_items?: any[];
}

export interface TrafficAnalyticsHistory {
    visits_history: HistoricalMetricPoint[];
    bounce_rate_history: HistoricalMetricPoint[];
    unique_visitors_history: HistoricalMetricPoint[];
    raw_items?: any[];
}

export interface HistoricalData {
    rank_overview?: HistoricalRankOverview;
    traffic_analytics?: TrafficAnalyticsHistory;
    backlinks_history?: Record<string, HistoricalMetricPoint[]>;
    timestamp: string;
}

export interface DomainAnalysisReport {
    domain_name: string;
    analysis_timestamp: string;
    status: 'pending' | 'in_progress' | 'completed' | 'failed';
    data_for_seo_metrics?: DataForSEOMetrics;
    wayback_machine_summary?: WaybackMachineSummary;
    llm_analysis?: LLMAnalysis;
    historical_data?: HistoricalData;
    raw_data_links?: {
        full_keywords_list_api: string;
        full_backlinks_list_api: string;
    };
    processing_time_seconds?: number;
    error_message?: string;
    backlinks_page_summary?: BulkPageSummaryResult;
}

export interface DataForSEOMetrics {
    domain_rating_dr?: number;
    organic_traffic_est?: number;
    total_referring_domains?: number;
    total_backlinks?: number;
    referring_domains_info?: ReferringDomain[];
    organic_keywords?: OrganicKeyword[];
    total_keywords?: number;
    organic_metrics?: OrganicMetrics;
    paid_metrics?: PaidMetrics;
}

export interface OrganicMetrics {
    pos_1: number;
    pos_2_3: number;
    pos_4_10: number;
    pos_11_20: number;
    pos_21_30: number;
    pos_31_40: number;
    pos_41_50: number;
    pos_51_60: number;
    pos_61_70: number;
    pos_71_80: number;
    pos_81_90: number;
    pos_91_100: number;
    etv: number;
    count: number;
    estimated_paid_traffic_cost: number;
    is_new: number;
    is_up: number;
    is_down: number;
    is_lost: number;
}

export interface PaidMetrics {
    pos_1: number;
    pos_2_3: number;
    pos_4_10: number;
    pos_11_20: number;
    pos_21_30: number;
    pos_31_40: number;
    pos_41_50: number;
    pos_51_60: number;
    pos_61_70: number;
    pos_71_80: number;
    pos_81_90: number;
    pos_91_100: number;
    etv: number;
    count: number;
    estimated_paid_traffic_cost: number;
    is_new: number;
    is_up: number;
    is_down: number;
    is_lost: number;
}

export interface OrganicKeyword {
    keyword_data?: {
        keyword?: string;
        keyword_properties?: {
            keyword_difficulty?: number;
        };
        keyword_info?: {
            search_volume?: number;
            cpc?: number;
            competition_level?: string;
            competition?: number;
        };
    };
    ranked_serp_element?: {
        serp_item?: {
            rank_absolute?: number;
            etv?: number;
            url?: string;
            title?: string;
            description?: string;
        };
    };
    keyword?: string;
    rank?: number;
    search_volume?: number;
    traffic_share?: number;
    cpc?: number;
    competition?: number;
    etv?: number;
    url?: string;
    title?: string;
    description?: string;
    keyword_difficulty?: number;
}

export interface WaybackMachineSummary {
    first_capture_year?: number;
    total_captures?: number;
    last_capture_date?: string;
    historical_risk_assessment?: string;
    earliest_snapshot_url?: string;
}

export interface LLMAnalysis {
    good_highlights?: string[];
    bad_highlights?: string[];
    suggested_niches?: string[];
    advantages_disadvantages_table?: AdvantageDisadvantage[];
    buy_recommendation?: BuyRecommendation;
    valuable_assets?: string[];
    major_concerns?: string[];
    content_strategy?: ContentStrategy;
    backlink_opportunities?: BacklinkOpportunities;
    investment_analysis?: InvestmentAnalysis;
    action_plan?: ActionPlan;
    pros_and_cons?: ProsAndCons[];
    summary?: string;
    confidence_score?: number;
}

export interface BuyRecommendation {
    recommendation: 'BUY' | 'NO-BUY' | 'CAUTION';
    confidence: number;
    reasoning: string;
    risk_level: 'low' | 'medium' | 'high';
    potential_value: 'high' | 'medium' | 'low';
}

export interface ContentStrategy {
    primary_niche: string;
    secondary_niches: string[];
    first_articles: string[];
    target_keywords: string[];
}

export interface BacklinkOpportunities {
    high_value_links: string[];
    content_angles: string[];
    link_building_strategy: string[];
}

export interface InvestmentAnalysis {
    seo_value: string;
    content_potential: string;
    competition_analysis: string;
    time_to_results: string;
    recommended_budget: string;
}

export interface ActionPlan {
    immediate_actions: string[];
    first_month: string[];
    long_term_strategy: string[];
}

export interface ProsAndCons {
    type: 'pro' | 'con';
    description: string;
    impact: 'high' | 'medium' | 'low';
    example: string;
}

export interface AdvantageDisadvantage {
    type: 'advantage' | 'disadvantage';
    description: string;
    metric: string;
}

export interface HealthResponse {
    status: string;
    timestamp: string;
    version: string;
    services: Record<string, string>;
}

export interface KeywordsResponse {
    domain: string;
    total_count: number;
    limit: number;
    offset: number;
    keywords: OrganicKeyword[];
}

export interface ReferringDomain {
    domain: string;
    domain_rank: number;
    anchor_text: string | null;
    backlinks_count: number;
    first_seen: string;
    last_seen: string;
    url_from?: string;
    url_to?: string;
    link_type?: string;
    link_attributes?: string;
    page_from_title?: string;
    page_from_rank?: number;
    page_from_internal_links_count?: number;
    page_from_external_links_count?: number;
    page_from_rank_absolute?: number;
    dofollow?: boolean;
    is_new?: boolean;
    is_lost?: boolean;
    is_broken?: boolean;
    url_from_https?: boolean;
    url_to_https?: boolean;
    page_from_status_code?: number;
    url_to_status_code?: number;
    backlink_spam_score?: number;
    url_to_spam_score?: number;
    page_from_size?: number;
    page_from_encoding?: string;
    page_from_language?: string;
    domain_from_ip?: string;
    domain_from_country?: string;
    domain_from_platform_type?: string[];
    semantic_location?: string;
    alt?: string;
    image_url?: string;
    text_pre?: string;
    text_post?: string;
    tld_from?: string;
    domain_to?: string;
    is_indirect_link?: boolean;
    indirect_link_path?: string;
    url_to_redirect_target?: string;
    prev_seen?: string;
    group_count?: number;
    original?: boolean;
    item_type?: string;
    domain_from_is_ip?: boolean;
}

export interface BacklinksResponse {
    domain: string;
    total_count: number;
    limit: number;
    offset: number;
    backlinks: ReferringDomain[];
}

export interface BulkPageSummaryInfo {
    server?: string;
    cms?: string;
    platform_type?: string[];
    ip_address?: string;
    country?: string;
    is_ip?: boolean;
    target_spam_score?: number;
}

export interface BulkPageSummaryResult {
    target: string;
    first_seen?: string;
    lost_date?: string;
    rank?: number;
    backlinks?: number;
    backlinks_spam_score?: number;
    crawled_pages?: number;
    info?: BulkPageSummaryInfo;
    internal_links_count?: number;
    external_links_count?: number;
    broken_backlinks?: number;
    broken_pages?: number;
    referring_domains?: number;
    referring_domains_nofollow?: number;
    referring_main_domains?: number;
    referring_main_domains_nofollow?: number;
    referring_ips?: number;
    referring_subnets?: number;
    referring_pages?: number;
    referring_pages_nofollow?: number;
    referring_links_tld?: Record<string, number>;
    referring_links_types?: Record<string, number>;
    referring_links_attributes?: Record<string, number>;
    referring_links_platform_types?: Record<string, number>;
}

export interface BulkDomainAnalysis {
    id: string;
    domain_name: string;
    provider?: string;
    backlinks_bulk_page_summary?: BulkPageSummaryResult;
    created_at?: string;
    updated_at?: string;
}

export interface BulkAnalysisUploadResponse {
    success: boolean;
    message: string;
    created_count: number;
    updated_count: number;
    skipped_count: number;
    triggered_count: number;
    domains_triggered: string[];
}

export interface BulkAnalysisListResponse {
    success: boolean;
    count: number;
    domains: BulkDomainAnalysis[];
}

export interface TriggerMissingResponse {
    success: boolean;
    triggered_count: number;
    domains: string[];
    message: string;
}

export interface NamecheapDomain {
    id: string;
    url?: string;
    name: string;
    start_date?: string;
    end_date?: string;
    price?: number;
    start_price?: number;
    renew_price?: number;
    bid_count?: number;
    ahrefs_domain_rating?: number;
    umbrella_ranking?: number;
    cloudflare_ranking?: number;
    estibot_value?: number;
    extensions_taken?: number;
    keyword_search_count?: number;
    registered_date?: string;
    last_sold_price?: number;
    last_sold_year?: number;
    is_partner_sale?: boolean;
    semrush_a_score?: number;
    majestic_citation?: number;
    ahrefs_backlinks?: number;
    semrush_backlinks?: number;
    majestic_backlinks?: number;
    majestic_trust_flow?: number;
    go_value?: number;
    created_at?: string;
    updated_at?: string;
    filter_status?: 'PASS' | 'FAIL';
    filter_reason?: string;
    total_meaning_score?: number;
    age_score?: number;
    lexical_frequency_score?: number;
    semantic_value_score?: number;
    rank?: number;
}

export interface NamecheapDomainListResponse {
    success: boolean;
    count: number;
    domains: NamecheapDomain[];
    total_count?: number;
    has_more?: boolean;
    scoring_stats?: {
        passed: number;
        failed: number;
    };
}

export interface NamecheapUploadResponse {
    success: boolean;
    message: string;
    loaded_count: number;
    skipped_count: number;
    total_count: number;
    file_id?: string;
    scoring_stats?: {
        passed: number;
        failed: number;
        top_score?: number;
    };
}

export interface NamecheapAnalysisResult {
    domain: string;
    namecheap_data?: NamecheapDomain;
    dataforseo_data?: BulkPageSummaryResult;
    has_data: boolean;
    status: 'pending' | 'has_data' | 'triggered' | 'error';
    error?: string;
}

export interface NamecheapAnalysisResponse {
    success: boolean;
    results: NamecheapAnalysisResult[];
    total_selected: number;
    has_data_count: number;
    triggered_count: number;
    error_count: number;
}

export interface Auction {
    id: string;
    domain: string;
    start_date?: string;
    expiration_date: string;
    auction_site: string;
    ranking?: number;
    score?: number;
    preferred: boolean;
    has_statistics: boolean;
    has_analysis?: boolean;
    current_bid?: number;
    offer_type?: string;
    link?: string;
    backlinks?: number;
    referring_domains?: number;
    backlinks_spam_score?: number;
    organic_traffic?: number;
    keywords_count?: number;
    domain_rating?: number;
    first_seen?: string;
    source_data?: Record<string, any>;
    page_statistics?: Record<string, any>;
    created_at?: string;
    updated_at?: string;
    statistics?: BulkPageSummaryResult;
}

export interface AuctionUploadResponse {
    success: boolean;
    job_id?: string;
    message: string;
    inserted?: number;
    updated?: number;
    skipped?: number;
    deleted_expired?: number;
    total_processed?: number;
    auction_site?: string;
    filename?: string;
}

export interface AuctionUploadProgress {
    success: boolean;
    job_id: string;
    status: 'pending' | 'parsing' | 'processing' | 'completed' | 'failed';
    filename: string;
    auction_site: string;
    total_records: number;
    processed_records: number;
    inserted_count: number;
    updated_count: number;
    skipped_count: number;
    deleted_expired_count: number;
    current_stage: string | null;
    progress_percentage: number;
    error_message: string | null;
    started_at: string;
    updated_at: string;
    completed_at: string | null;
}

export interface AuctionTriggerResponse {
    success: boolean;
    message: string;
    triggered_count: number;
    skipped_count: number;
    triggered_domains: string[];
}

export interface AuctionReportResponse {
    success: boolean;
    count: number;
    total_count: number;
    has_more: boolean;
    auctions: Auction[];
}

export interface BalanceResponse {
    user_id: string;
    balance: number;
    currency: string;
}

export interface TransactionResponse {
    id: string;
    amount: number;
    transaction_type: string;
    description: string;
    reference_id?: string;
    balance_after: number;
    created_at: string;
}

export interface PurchaseRequest {
    amount: number;
    description?: string;
    reference_id?: string;
}

export interface PurchaseResponse {
    success: boolean;
    new_balance: number;
    message: string;
}
