import React, { createContext, useContext, ReactNode } from 'react';
import axios, { AxiosInstance, AxiosResponse } from 'axios';

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

export interface DomainAnalysisReport {
  domain_name: string;
  analysis_timestamp: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  data_for_seo_metrics?: DataForSEOMetrics;
  wayback_machine_summary?: WaybackMachineSummary;
  llm_analysis?: LLMAnalysis;
  raw_data_links?: {
    full_keywords_list_api: string;
    full_backlinks_list_api: string;
  };
  processing_time_seconds?: number;
  error_message?: string;
}

export interface DataForSEOMetrics {
  domain_rating_dr?: number;
  organic_traffic_est?: number;
  total_referring_domains?: number;
  total_backlinks?: number;
  referring_domains_info?: ReferringDomain[];
  organic_keywords?: OrganicKeyword[];
}

export interface ReferringDomain {
  domain: string;
  domain_rank: number;
  anchor_text: string;
  backlinks_count: number;
  first_seen: string;
  last_seen: string;
}

export interface OrganicKeyword {
  keyword: string;
  rank: number;
  search_volume: number;
  traffic_share: number;
  cpc: number;
  competition: number;
}

export interface WaybackMachineSummary {
  first_capture_year?: number;
  total_captures?: number;
  last_capture_date?: string;
  historical_risk_assessment?: string;
  earliest_snapshot_url?: string;
}

export interface LLMAnalysis {
  good_highlights: string[];
  bad_highlights: string[];
  suggested_niches: string[];
  advantages_disadvantages_table: AdvantageDisadvantage[];
  summary?: string;
  confidence_score?: number;
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

export interface BacklinksResponse {
  domain: string;
  total_count: number;
  limit: number;
  offset: number;
  backlinks: ReferringDomain[];
}

// API Service Class
class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
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
        console.error('API Response Error:', error.response?.data || error.message);
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
  async analyzeDomain(domain: string): Promise<AnalysisResponse> {
    const response: AxiosResponse<AnalysisResponse> = await this.client.post('/analyze', {
      domain,
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
    limit: number = 100,
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
    limit: number = 100,
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

  async deleteReport(domain: string): Promise<{ success: boolean; message: string }> {
    const response: AxiosResponse<{ success: boolean; message: string }> = await this.client.delete(
      `/reports/${domain}`
    );
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
