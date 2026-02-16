import React, { createContext, useContext, ReactNode } from 'react';
import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { supabase } from '../supabaseClient';

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
  domain_rating_dr?: number; // DataForSEO Rank (PageRank-like metric, 0-100 scale)
  organic_traffic_est?: number;
  total_referring_domains?: number;
  total_backlinks?: number;
  referring_domains_info?: ReferringDomain[];
  organic_keywords?: OrganicKeyword[];
  // Domain rank overview data
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
  // Flattened properties for backward compatibility
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
  // Legacy fields for backward compatibility
  good_highlights?: string[];
  bad_highlights?: string[];
  suggested_niches?: string[];
  advantages_disadvantages_table?: AdvantageDisadvantage[];

  // New domain buyer-focused fields
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
  // Additional comprehensive fields from DataForSEO
  url_from?: string;
  url_to?: string;
  link_type?: string;
  link_attributes?: string;
  page_from_title?: string;
  page_from_rank?: number;
  page_from_internal_links_count?: number;
  page_from_external_links_count?: number;
  page_from_rank_absolute?: number;
  // Additional useful fields
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

// Bulk Domain Analysis Interfaces
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

// Namecheap Domain Interfaces
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
  // Scoring fields
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
  file_id?: string; // For CSV viewing mode
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

// Auctions Types
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
  current_bid?: number;
  offer_type?: string; // Type of domain offering: 'auction', 'backorder', 'buy_now'
  link?: string; // Direct link to auction listing (e.g., GoDaddy auction URL)
  // Extracted columns from page_statistics for better query performance
  backlinks?: number;
  referring_domains?: number;
  backlinks_spam_score?: number;
  first_seen?: string;
  source_data?: Record<string, any>;
  page_statistics?: Record<string, any>; // DataForSEO page statistics from auctions table (full JSONB)
  created_at?: string;
  updated_at?: string;
  statistics?: BulkPageSummaryResult; // From bulk_domain_analysis (legacy)
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

// Credits Response Types
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

// API Service Class
class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.REACT_APP_API_URL || '/api/v1',
      timeout: 1800000, // 30 minutes default for large operations (can be overridden per request)
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      async (config) => {
        // Get the session from Supabase
        try {
          const { data: { session } } = await supabase.auth.getSession();
          if (session?.access_token) {
            config.headers.Authorization = `Bearer ${session.access_token}`;
          }
        } catch (error) {
          console.error('Error getting session for API request:', error);
        }

        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('API Request Error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        console.log(`API Response: ${response.status} ${response.config.url}`);
        return response;
      },
      (error) => {
        console.error('API Response Error:', {
          url: error.config?.url,
          method: error.config?.method,
          status: error.response?.status,
          data: error.response?.data,
          message: error.message
        });
        return Promise.reject(error);
      }
    );
  }

  // Health Check
  async getHealth(): Promise<HealthResponse> {
    const response: AxiosResponse<HealthResponse> = await this.client.get('/health');
    return response.data;
  }

  // Domain Analysis
  async analyzeDomain(domain: string, mode: string = 'dual'): Promise<AnalysisResponse> {
    const response: AxiosResponse<AnalysisResponse> = await this.client.post('/analyze', {
      domain,
      mode,
    });
    return response.data;
  }

  async getAnalysisStatus(domain: string): Promise<AnalysisResponse> {
    const response: AxiosResponse<AnalysisResponse> = await this.client.get(`/analyze/${domain}`);
    return response.data;
  }

  async cancelAnalysis(domain: string): Promise<{ success: boolean; message: string }> {
    const response: AxiosResponse<{ success: boolean; message: string }> = await this.client.delete(
      `/analyze/${domain}`
    );
    return response.data;
  }

  async retryAnalysis(domain: string): Promise<AnalysisResponse> {
    const response: AxiosResponse<AnalysisResponse> = await this.client.post(
      `/analyze/${domain}/retry`
    );
    return response.data;
  }

  // Reports
  async getReport(domain: string): Promise<ReportResponse> {
    const response: AxiosResponse<ReportResponse> = await this.client.get(`/reports/${domain}`);
    return response.data;
  }

  async getAnalysisProgress(domain: string): Promise<ProgressResponse> {
    const response: AxiosResponse<ProgressResponse> = await this.client.get(`/reports/${domain}/progress`);
    return response.data;
  }

  async listReports(
    limit: number = 10,
    offset: number = 0,
    status?: string
  ): Promise<DomainAnalysisReport[]> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });
    if (status) {
      params.append('status', status);
    }

    const response: AxiosResponse<DomainAnalysisReport[]> = await this.client.get(
      `/reports?${params.toString()}`
    );
    return response.data;
  }

  async getKeywords(
    domain: string,
    limit: number = 50, // Reduced default to prevent timeouts with large JSONB responses
    offset: number = 0
  ): Promise<KeywordsResponse> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });

    const response: AxiosResponse<KeywordsResponse> = await this.client.get(
      `/reports/${domain}/keywords?${params.toString()}`
    );
    return response.data;
  }

  async getBacklinks(
    domain: string,
    limit: number = 50, // Reduced default to prevent timeouts with large JSONB responses
    offset: number = 0
  ): Promise<BacklinksResponse> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });

    const response: AxiosResponse<BacklinksResponse> = await this.client.get(
      `/reports/${domain}/backlinks?${params.toString()}`
    );
    return response.data;
  }

  async getPageSummary(domain: string): Promise<{
    success: boolean;
    data?: BulkPageSummaryResult;
    message?: string;
  }> {
    const response = await this.client.get(`/reports/${domain}/page-summary`);
    return response.data;
  }

  async getHistoricalData(domain: string): Promise<HistoricalData> {
    const response: AxiosResponse<HistoricalData> = await this.client.get(`/reports/${domain}/history`);
    return response.data;
  }

  async exportBacklinks(domain: string): Promise<BacklinksResponse> {
    const response: AxiosResponse<BacklinksResponse> = await this.client.get(
      `/reports/${domain}/backlinks/export`
    );
    return response.data;
  }

  async exportKeywords(domain: string): Promise<KeywordsResponse> {
    const response: AxiosResponse<KeywordsResponse> = await this.client.get(
      `/reports/${domain}/keywords/export`
    );
    return response.data;
  }

  async deleteReport(domain: string): Promise<{ success: boolean; message: string }> {
    const response: AxiosResponse<{ success: boolean; message: string }> = await this.client.delete(
      `/reports/${domain}`
    );
    return response.data;
  }

  async reanalyzeAI(
    domain: string,
    includeBacklinks: boolean = false,
    includeKeywords: boolean = false
  ): Promise<{ success: boolean; message: string; llm_analysis: LLMAnalysis }> {
    const response: AxiosResponse<{ success: boolean; message: string; llm_analysis: LLMAnalysis }> =
      await this.client.post(`/reports/${domain}/reanalyze`, {
        include_backlinks: includeBacklinks,
        include_keywords: includeKeywords
      });
    return response.data;
  }

  // Development Plan
  async generateDevelopmentPlan(domain: string): Promise<{ plan: any }> {
    const response: AxiosResponse<{ plan: any }> = await this.client.post('/development-plan', {
      domain,
    });
    return response.data;
  }

  // Namecheap Domain Analysis
  async uploadNamecheapCSV(file: File, loadToDb: boolean = false): Promise<NamecheapUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response: AxiosResponse<NamecheapUploadResponse> = await this.client.post(
      `/bulk-analysis/namecheap/upload-csv?load_to_db=${loadToDb}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000, // 5 minutes for large CSV files
      }
    );
    return response.data;
  }

  async getCSVNamecheapDomains(
    fileId: string,
    sortBy: string = 'name',
    order: string = 'asc',
    search?: string,
    extensions?: string[],
    noSpecialChars?: boolean,
    noNumbers?: boolean,
    filterStatus?: 'PASS' | 'FAIL' | 'ALL',
    limit: number = 50, // Reduced default to prevent timeouts with large JSONB responses
    offset: number = 0
  ): Promise<NamecheapDomainListResponse> {
    const params = new URLSearchParams({
      file_id: fileId,
      sort_by: sortBy,
      order: order,
      limit: limit.toString(),
      offset: offset.toString(),
    });

    if (search) {
      params.append('search', search);
    }

    if (extensions && extensions.length > 0) {
      params.append('extensions', extensions.join(','));
    }

    if (noSpecialChars !== undefined) {
      params.append('no_special_chars', noSpecialChars.toString());
    }

    if (noNumbers !== undefined) {
      params.append('no_numbers', noNumbers.toString());
    }

    if (filterStatus && filterStatus !== 'ALL') {
      params.append('filter_status', filterStatus);
    }

    const response: AxiosResponse<NamecheapDomainListResponse> = await this.client.get(
      `/bulk-analysis/namecheap/csv-domains?${params.toString()}`
    );
    return response.data;
  }

  async getNamecheapDomains(
    sortBy: string = 'name',
    order: string = 'asc',
    search?: string,
    extensions?: string[],
    noSpecialChars?: boolean,
    noNumbers?: boolean
  ): Promise<NamecheapDomainListResponse> {
    const params = new URLSearchParams({
      sort_by: sortBy,
      order: order,
    });

    if (search) {
      params.append('search', search);
    }

    // Only add extensions param if there are actual extensions to filter
    if (extensions && extensions.length > 0) {
      params.append('extensions', extensions.join(','));
    }
    // If extensions is undefined or empty array, don't add the param (shows all)

    if (noSpecialChars !== undefined) {
      params.append('no_special_chars', noSpecialChars.toString());
    }

    if (noNumbers !== undefined) {
      params.append('no_numbers', noNumbers.toString());
    }

    const response: AxiosResponse<NamecheapDomainListResponse> = await this.client.get(
      `/bulk-analysis/namecheap/domains?${params.toString()}`
    );
    return response.data;
  }

  async analyzeSelectedDomains(
    domainNames: string[]
  ): Promise<NamecheapAnalysisResponse> {
    const response: AxiosResponse<NamecheapAnalysisResponse> = await this.client.post(
      '/bulk-analysis/namecheap/analyze-selected',
      { domain_names: domainNames }
    );
    return response.data;
  }

  async getScoredDomains(
    fileId: string,
    limit: number = 1500,
    offset: number = 0
  ): Promise<NamecheapDomainListResponse & { scoring_stats?: { passed: number; failed: number } }> {
    const response = await this.client.get('/bulk-analysis/namecheap/scored-domains', {
      params: { file_id: fileId, limit, offset },
    });
    return response.data;
  }

  async autoTriggerAnalysis(
    fileId: string,
    topN: number = 1000,
    topRankThreshold: number = 3000
  ): Promise<{
    success: boolean;
    triggered_count: number;
    skipped_count: number;
    domains: string[];
    message: string;
    request_id?: string;
  }> {
    const response = await this.client.post('/bulk-analysis/namecheap/auto-trigger-analysis', {
      file_id: fileId,
      top_n: topN,
      top_rank_threshold: topRankThreshold,
    });
    return response.data;
  }

  // Auctions API Methods
  async uploadAuctionsCSV(file: File, auctionSite: string, offeringType?: string): Promise<AuctionUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    let url = `/auctions/upload-csv?auction_site=${encodeURIComponent(auctionSite)}`;
    if (offeringType) {
      url += `&offering_type=${encodeURIComponent(offeringType)}`;
    }

    const response: AxiosResponse<AuctionUploadResponse> = await this.client.post(
      url,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 1800000, // 30 minutes for very large CSV files (800K+ records)
      }
    );
    return response.data;
  }

  async uploadAuctionsJSON(file: File, auctionSite: string, offeringType?: string): Promise<AuctionUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    let url = `/auctions/upload-json?auction_site=${encodeURIComponent(auctionSite)}`;
    if (offeringType) {
      url += `&offering_type=${encodeURIComponent(offeringType)}`;
    }

    const response: AxiosResponse<AuctionUploadResponse> = await this.client.post(
      url,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 1800000, // 30 minutes for very large JSON files
      }
    );
    return response.data;
  }

  async triggerAuctionsAnalysis(limit: number = 100): Promise<AuctionTriggerResponse> { // DataForSEO limit: 100 unique domains per request
    const response: AxiosResponse<AuctionTriggerResponse> = await this.client.post(
      `/auctions/trigger-analysis?limit=${limit}`,
      {},
      {
        timeout: 300000, // 5 minutes
      }
    );
    return response.data;
  }

  async triggerBulkRankAnalysis(limit: number = 1000): Promise<AuctionTriggerResponse> { // DataForSEO bulk rank limit: 1000 domains per request
    const response: AxiosResponse<AuctionTriggerResponse> = await this.client.post(
      `/auctions/trigger-bulk-rank?limit=${limit}`,
      {},
      {
        timeout: 300000, // 5 minutes
      }
    );
    return response.data;
  }

  async triggerBulkBacklinksAnalysis(limit: number = 1000): Promise<AuctionTriggerResponse> { // DataForSEO bulk backlinks limit: 1000 domains per request
    const response: AxiosResponse<AuctionTriggerResponse> = await this.client.post(
      `/auctions/trigger-bulk-backlinks?limit=${limit}`,
      {},
      {
        timeout: 300000, // 5 minutes
      }
    );
    return response.data;
  }

  async triggerBulkSpamScoreAnalysis(limit: number = 1000): Promise<AuctionTriggerResponse> { // DataForSEO bulk spam score limit: 1000 domains per request
    const response: AxiosResponse<AuctionTriggerResponse> = await this.client.post(
      `/auctions/trigger-bulk-spam-score?limit=${limit}`,
      {},
      {
        timeout: 300000, // 5 minutes
      }
    );
    return response.data;
  }

  async triggerBulkTrafficDataAnalysis(limit: number = 1000): Promise<AuctionTriggerResponse> { // DataForSEO Labs API limit: 1000 domains per request
    const response: AxiosResponse<AuctionTriggerResponse> = await this.client.post(
      `/auctions/trigger-bulk-traffic-data?limit=${limit}`,
      {},
      {
        timeout: 300000, // 5 minutes
      }
    );
    return response.data;
  }

  async triggerBulkAllMetricsAnalysis(filters: {
    preferred?: boolean;
    auctionSite?: string;
    offeringType?: string;
    tld?: string;
    tlds?: string[];
    hasStatistics?: boolean;
    scored?: boolean;
    minRank?: number;
    maxRank?: number;
    minScore?: number;
    maxScore?: number;
    expirationFromDate?: string;
    expirationToDate?: string;
    sortBy?: string;
    sortOrder?: string;
    limit?: number;
  }): Promise<{
    success: boolean;
    message: string;
    triggered_count: number;
    skipped_count: number;
    triggered_domains: string[];
    results: {
      traffic_data: { triggered: number; success: boolean; request_id?: string; error?: string };
      rank: { triggered: number; success: boolean; request_id?: string; error?: string };
      backlinks: { triggered: number; success: boolean; request_id?: string; error?: string };
      spam_score: { triggered: number; success: boolean; request_id?: string; error?: string };
    };
  }> {
    const params = new URLSearchParams();

    if (filters.preferred !== undefined) {
      params.append('preferred', filters.preferred.toString());
    }
    if (filters.auctionSite) {
      params.append('auction_site', filters.auctionSite);
    }
    if (filters.offeringType) {
      params.append('offering_type', filters.offeringType);
    }
    if (filters.tlds && filters.tlds.length > 0) {
      params.append('tlds', filters.tlds.join(','));
    } else if (filters.tld) {
      params.append('tld', filters.tld);
    }
    if (filters.hasStatistics !== undefined) {
      params.append('has_statistics', filters.hasStatistics.toString());
    }
    if (filters.scored !== undefined) {
      params.append('scored', filters.scored.toString());
    }
    if (filters.minRank !== undefined) {
      params.append('min_rank', filters.minRank.toString());
    }
    if (filters.maxRank !== undefined) {
      params.append('max_rank', filters.maxRank.toString());
    }
    if (filters.minScore !== undefined) {
      params.append('min_score', filters.minScore.toString());
    }
    if (filters.maxScore !== undefined) {
      params.append('max_score', filters.maxScore.toString());
    }
    if (filters.expirationFromDate) {
      params.append('expiration_from_date', filters.expirationFromDate);
    }
    if (filters.expirationToDate) {
      params.append('expiration_to_date', filters.expirationToDate);
    }
    if (filters.sortBy) {
      params.append('sort_by', filters.sortBy);
    }
    if (filters.sortOrder) {
      params.append('sort_order', filters.sortOrder);
    }
    if (filters.limit !== undefined) {
      params.append('limit', filters.limit.toString());
    }

    const response: AxiosResponse = await this.client.post(
      `/auctions/trigger-bulk-all-metrics?${params.toString()}`,
      {},
      {
        timeout: 300000, // 5 minutes
      }
    );
    return response.data;
  }

  async getUploadProgress(jobId: string): Promise<AuctionUploadProgress> {
    const response: AxiosResponse<AuctionUploadProgress> = await this.client.get(
      `/auctions/upload-progress/${jobId}`,
      {
        timeout: 30000, // 30 seconds
      }
    );
    return response.data;
  }

  async getLatestActiveUploadProgress(): Promise<AuctionUploadProgress | null> {
    try {
      const response: AxiosResponse<AuctionUploadProgress> = await this.client.get(
        `/auctions/upload-progress/latest-active`,
        {
          timeout: 10000, // 10 seconds - reduced from 30 to avoid long waits
        }
      );
      return response.data;
    } catch (error: any) {
      // Return null if no active job found (404) or timeout
      if (error.response?.status === 404 || error.code === 'ECONNABORTED') {
        return null;
      }
      // For other errors, log and return null
      console.error('Failed to get latest active upload progress:', error);
      return null;
    }
  }

  async getAuctionsReport(
    preferred?: boolean,
    auctionSite?: string,
    offeringType?: string,
    tld?: string,
    tlds?: string[],
    hasStatistics?: boolean,
    scored?: boolean,
    minRank?: number,
    maxRank?: number,
    minScore?: number,
    maxScore?: number,
    expirationFromDate?: string,
    expirationToDate?: string,
    auctionSites?: string[],
    sortBy: string = 'expiration_date',
    order: string = 'asc',
    limit: number = 50, // Reduced default to prevent timeouts with large JSONB responses
    offset: number = 0
  ): Promise<AuctionReportResponse> {
    const params = new URLSearchParams({
      sort_by: sortBy,
      order: order,
      limit: limit.toString(),
      offset: offset.toString(),
    });

    if (preferred !== undefined) {
      params.append('preferred', preferred.toString());
    }
    if (scored !== undefined) {
      params.append('scored', scored.toString());
    }
    if (minRank !== undefined) {
      params.append('min_rank', minRank.toString());
    }
    if (maxRank !== undefined) {
      params.append('max_rank', maxRank.toString());
    }
    if (minScore !== undefined) {
      params.append('min_score', minScore.toString());
    }
    if (maxScore !== undefined) {
      params.append('max_score', maxScore.toString());
    }

    if (auctionSites && auctionSites.length > 0) {
      params.append('auction_sites', auctionSites.join(','));
    } else if (auctionSite) {
      params.append('auction_site', auctionSite);
    }

    if (offeringType) {
      params.append('offering_type', offeringType);
    }

    if (tlds && tlds.length > 0) {
      params.append('tlds', tlds.join(','));
    } else if (tld) {
      params.append('tld', tld);
    }

    if (expirationFromDate) {
      params.append('expiration_from_date', expirationFromDate);
    }
    if (expirationToDate) {
      params.append('expiration_to_date', expirationToDate);
    }

    if (hasStatistics !== undefined) {
      params.append('has_statistics', hasStatistics.toString());
    }

    const response: AxiosResponse<AuctionReportResponse> = await this.client.get(
      `/auctions/report?${params.toString()}`
    );
    return response.data;
  }

  async getUniqueTlds(): Promise<string[]> {
    const response: AxiosResponse<{ tlds: string[] }> = await this.client.get('/auctions/tlds');
    return response.data.tlds;
  }

  async fetchWaybackFirstSeen(domain: string): Promise<{
    success: boolean;
    first_seen?: string;
    first_seen_year?: number;
    message?: string;
    updated_count?: number;
  }> {
    // Use a shorter timeout for Wayback Machine calls (15 seconds)
    const response: AxiosResponse = await this.client.post(
      `/auctions/${encodeURIComponent(domain)}/wayback-first-seen`,
      {},
      { timeout: 15000 }
    );
    return response.data;
  }

  async queueDomainForDataForSEO(domain: string): Promise<{
    success: boolean;
    message: string;
    queued: boolean;
    position?: number;
    queue_count?: number;
    will_process?: boolean;
  }> {
    const response: AxiosResponse = await this.client.post(
      `/auctions/${encodeURIComponent(domain)}/queue-dataforseo`
    );
    return response.data;
  }

  async getDataForSEOQueueStatus(domain?: string): Promise<{
    queue_count: number;
    max_queue_size: number;
    ready_to_process: boolean;
    domain_queued?: boolean;
    position?: number;
  }> {
    const params = domain ? { domain } : {};
    const response: AxiosResponse = await this.client.get(
      `/auctions/dataforseo-queue/status`,
      { params }
    );
    return response.data;
  }

  async cancelDomainQueueRequest(domain: string): Promise<{
    success: boolean;
    message: string;
    cancelled: boolean;
  }> {
    const response: AxiosResponse = await this.client.delete(
      `/auctions/${encodeURIComponent(domain)}/queue-dataforseo`
    );
    return response.data;
  }

  // Scoring and Ranking
  async processScoringBatch(batchSize: number = 10000, configId?: string, recalculateRankings: boolean = false): Promise<{
    success: boolean;
    processed_count: number;
    total_fetched: number;
    ranking_stats?: any;
    error?: string;
  }> {
    const params = new URLSearchParams({
      batch_size: batchSize.toString(),
      recalculate_rankings: recalculateRankings.toString(),
    });
    if (configId) {
      params.append('config_id', configId);
    }
    const response: AxiosResponse = await this.client.post(`/auctions/process-scoring-batch?${params.toString()}`);
    return response.data;
  }

  async getScoringStats(): Promise<{
    unprocessed_count: number;
    processed_count: number;
    scored_count: number;
    total_count: number;
  }> {
    const response: AxiosResponse = await this.client.get('/auctions/scoring-stats');
    return response.data;
  }

  async recalculateRankings(): Promise<{
    success: boolean;
    ranked_count?: number;
    preferred_count?: number;
    execution_time_seconds?: number;
    error?: string;
  }> {
    const response: AxiosResponse = await this.client.post('/auctions/recalculate-rankings');
    return response.data;
  }

  // Filters API
  async getFilters(userId?: string): Promise<{
    success: boolean;
    filter: {
      id?: string;
      preferred?: boolean;
      auction_site?: string;
      tld?: string;
      tlds?: string[];
      has_statistics?: boolean;
      scored?: boolean;
      min_rank?: number;
      max_rank?: number;
      min_score?: number;
      max_score?: number;
      expiration_from_date?: string;
      expiration_to_date?: string;
      auction_sites?: string[];
      show_expired?: boolean;
      sort_by: string;
      sort_order: string;
      page_size: number;
      filter_name: string;
    };
  }> {
    const params = userId ? `?user_id=${encodeURIComponent(userId)}` : '';
    const response: AxiosResponse = await this.client.get(`/filters${params}`);
    return response.data;
  }

  async updateFilters(filterSettings: {
    preferred?: boolean;
    auction_site?: string;
    tld?: string;
    tlds?: string[];
    has_statistics?: boolean;
    scored?: boolean;
    min_rank?: number;
    max_rank?: number;
    min_score?: number;
    max_score?: number;
    expiration_from_date?: string;
    expiration_to_date?: string;
    auction_sites?: string[];
    show_expired?: boolean;
    sort_by?: string;
    sort_order?: string;
    page_size?: number;
    filter_name?: string;
    is_default?: boolean;
  }, userId?: string): Promise<{
    success: boolean;
    message: string;
  }> {
    const params = userId ? `?user_id=${encodeURIComponent(userId)}` : '';
    const response: AxiosResponse = await this.client.put(`/filters${params}`, filterSettings);
    return response.data;
  }

  // Legacy Bulk Domain Analysis (kept for backward compatibility)

  async getBulkDomains(
    sortBy: string = 'created_at',
    order: string = 'desc'
  ): Promise<BulkAnalysisListResponse> {
    const params = new URLSearchParams({
      sort_by: sortBy,
      order: order,
    });

    const response: AxiosResponse<BulkAnalysisListResponse> = await this.client.get(
      `/bulk-analysis/domains?${params.toString()}`
    );
    return response.data;
  }

  async triggerMissingSummaries(): Promise<TriggerMissingResponse> {
    const response: AxiosResponse<TriggerMissingResponse> = await this.client.post(
      '/bulk-analysis/trigger-missing'
    );
    return response.data;
  }

  // Credits API Methods
  async getBalance(): Promise<BalanceResponse> {
    const response: AxiosResponse<BalanceResponse> = await this.client.get('/credits/balance');
    return response.data;
  }

  async getTransactions(limit: number = 20, offset: number = 0): Promise<TransactionResponse[]> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });
    const response: AxiosResponse<TransactionResponse[]> = await this.client.get(
      `/credits/transactions?${params.toString()}`
    );
    return response.data;
  }

  async purchaseCredits(amount: number, description: string = 'Credit purchase'): Promise<PurchaseResponse> {
    const response: AxiosResponse<PurchaseResponse> = await this.client.post('/credits/purchase', {
      amount,
      description,
    });
    return response.data;
  }

  // Utility methods
  formatDomain(domain: string): string {
    return domain.replace(/^https?:\/\//, '').replace(/^www\./, '').toLowerCase().trim();
  }

  validateDomain(domain: string): boolean {
    const domainRegex = /^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$/;
    return domainRegex.test(domain);
  }
}

// Create API service instance
const apiService = new ApiService();

// Context for API service
const ApiContext = createContext<ApiService | null>(null);

// API Provider component
export const ApiProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  return <ApiContext.Provider value={apiService}>{children}</ApiContext.Provider>;
};

// Hook to use API service
export const useApi = (): ApiService => {
  const context = useContext(ApiContext);
  if (!context) {
    throw new Error('useApi must be used within an ApiProvider');
  }
  return context;
};

export default apiService;
