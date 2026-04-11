import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, firstValueFrom } from 'rxjs';
import { environment } from '../../environments/environment';
import * as Models from '../models/domain.model';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  /**
   * Health Check
   */
  getHealth(): Observable<Models.HealthResponse> {
    return this.http.get<Models.HealthResponse>(`${this.baseUrl}/health`);
  }

  /**
   * Domain Analysis
   */
  analyzeDomain(domain: string, mode: string = 'dual'): Observable<Models.AnalysisResponse> {
    return this.http.post<Models.AnalysisResponse>(`${this.baseUrl}/analyze`, { domain, mode });
  }

  getAnalysisStatus(domain: string): Observable<Models.AnalysisResponse> {
    return this.http.get<Models.AnalysisResponse>(`${this.baseUrl}/analyze/${domain}`);
  }

  cancelAnalysis(domain: string): Observable<{ success: boolean; message: string }> {
    return this.http.delete<{ success: boolean; message: string }>(`${this.baseUrl}/analyze/${domain}`);
  }

  retryAnalysis(domain: string): Observable<Models.AnalysisResponse> {
    return this.http.post<Models.AnalysisResponse>(`${this.baseUrl}/analyze/${domain}/retry`, {});
  }

  /**
   * Reports
   */
  getReport(domain: string): Observable<Models.ReportResponse> {
    return this.http.get<Models.ReportResponse>(`${this.baseUrl}/reports/${domain}`);
  }

  downloadExecutivePdf(domain: string): Observable<Blob> {
    return this.http.get(`${this.baseUrl}/reports/${domain}/export/pdf`, {
      responseType: 'blob'
    });
  }

  deleteReport(domain: string): Observable<{ success: boolean; message: string }> {
    return this.http.delete<{ success: boolean; message: string }>(`${this.baseUrl}/reports/${domain}`);
  }

  getAnalysisProgress(domain: string): Observable<Models.ProgressResponse> {
    return this.http.get<Models.ProgressResponse>(`${this.baseUrl}/reports/${domain}/progress`);
  }

  getBacklinks(domain: string): Observable<{ domain: string; total_count: number; backlinks: any[] }> {
    return this.http.get<{ domain: string; total_count: number; backlinks: any[] }>(`${this.baseUrl}/reports/${domain}/backlinks`);
  }

  getKeywords(domain: string): Observable<{ domain: string; total_count: number; keywords: any[] }> {
    return this.http.get<{ domain: string; total_count: number; keywords: any[] }>(`${this.baseUrl}/reports/${domain}/keywords`);
  }

  getReportDetails(domain: string, options: { keywordsLimit?: number; backlinksLimit?: number; keywordsOffset?: number; backlinksOffset?: number; sections?: string[] } = {}): Observable<Models.ReportDetailsResponse> {
    const params = new HttpParams()
      .set('keywords_limit', (options.keywordsLimit ?? 100).toString())
      .set('backlinks_limit', (options.backlinksLimit ?? 100).toString())
      .set('keywords_offset', (options.keywordsOffset ?? 0).toString())
      .set('backlinks_offset', (options.backlinksOffset ?? 0).toString());

    const finalParams = options.sections?.length
      ? params.set('sections', options.sections.join(','))
      : params;

    return this.http.get<Models.ReportDetailsResponse>(`${this.baseUrl}/reports/${domain}/details`, { params: finalParams });
  }

  listReports(limit: number = 10, offset: number = 0, status?: string): Observable<Models.DomainAnalysisReport[]> {
    let params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());

    if (status) {
      params = params.set('status', status);
    }

    return this.http.get<Models.DomainAnalysisReport[]>(`${this.baseUrl}/reports`, { params });
  }

  /**
   * Auctions & Marketplace
   */
  getAuctionsReport(filters: any = {}): Observable<Models.AuctionReportResponse> {
    let params = new HttpParams();
    Object.keys(filters).forEach(key => {
      if (filters[key] !== undefined && filters[key] !== null) {
        if (Array.isArray(filters[key])) {
          params = params.set(key, filters[key].join(','));
        } else {
          params = params.set(key, filters[key].toString());
        }
      }
    });

    return this.http.get<Models.AuctionReportResponse>(`${this.baseUrl}/auctions/report`, { params });
  }

  /**
   * Credits & Billing
   */
  getBalance(): Observable<Models.BalanceResponse> {
    return this.http.get<Models.BalanceResponse>(`${this.baseUrl}/credits/balance`);
  }

  getTransactions(limit: number = 20, offset: number = 0): Observable<Models.TransactionResponse[]> {
    const params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());

    return this.http.get<Models.TransactionResponse[]>(`${this.baseUrl}/credits/transactions`, { params });
  }

  purchaseCredits(amount: number, description: string = 'Credit purchase'): Observable<Models.PurchaseResponse> {
    return this.http.post<Models.PurchaseResponse>(`${this.baseUrl}/credits/purchase`, {
      amount,
      description
    });
  }

  getPaymentHistory(limit: number = 20, offset: number = 0): Observable<Models.TransactionResponse[]> {
    const params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());

    return this.http.get<Models.TransactionResponse[]>(`${this.baseUrl}/credits/payments`, { params });
  }

  triggerDomainRefresh(domain: string): Observable<{ success: boolean; message: string; credits_deducted: number }> {
    return this.http.post<{ success: boolean; message: string; credits_deducted: number }>(
      `${this.baseUrl}/auctions/domain-refresh`,
      { domain }
    );
  }

  triggerBulkRefresh(filters: any, force: boolean = false, sort_by: string = 'expiration_date', sort_order: string = 'asc', prioritized_domains?: string[], only_displayed?: boolean): Observable<{ success: boolean; message: string; job_id: string; in_progress: boolean }> {
    return this.http.post<{ success: boolean; message: string; job_id: string; in_progress: boolean }>(
      `${this.baseUrl}/auctions/bulk-refresh`,
      { filters, force, sort_by, sort_order, prioritized_domains, only_displayed }
    );
  }

  triggerForceRefresh(filters: any, sort_by: string = 'expiration_date', sort_order: string = 'asc', prioritized_domains?: string[], only_displayed?: boolean): Observable<{ success: boolean; message: string; job_id: string; in_progress: boolean }> {
    return this.http.post<{ success: boolean; message: string; job_id: string; in_progress: boolean }>(
      `${this.baseUrl}/auctions/force-refresh`,
      { filters, sort_by, sort_order, prioritized_domains, only_displayed }
    );
  }

  getRefreshStatus(jobId: string): Observable<{
    success: boolean;
    job_id: string;
    status: string;
    progress_percent: number;
    total_items: number;
    processed_items: number;
    failed_items: number;
    current_batch: number;
    total_batches: number;
    message: string;
    started_at: string;
    completed_at: string | null;
  }> {
    return this.http.get<any>(`${this.baseUrl}/auctions/refresh-status/${jobId}`);
  }

  getRefreshPreview(filters: any, force: boolean = false): Observable<{ success: boolean; domain_count: number; would_refresh: boolean; message: string }> {
    return this.http.post<{ success: boolean; domain_count: number; would_refresh: boolean; message: string }>(
      `${this.baseUrl}/auctions/refresh-preview`,
      { filters, force }
    );
  }

  togglePreferredAuction(id: string, preferred: boolean): Observable<{ success: boolean }> {
    return this.http.post<{ success: boolean }>(
      `${this.baseUrl}/auctions/${id}/preferred`,
      { preferred }
    );
  }

  getLatestActiveUploadProgress(): Observable<Models.AuctionUploadProgress> {
    return this.http.get<Models.AuctionUploadProgress>(`${this.baseUrl}/auctions/upload-progress/latest-active`);
  }

  getUploadProgress(jobId: string): Observable<Models.AuctionUploadProgress> {
    return this.http.get<Models.AuctionUploadProgress>(`${this.baseUrl}/auctions/upload-progress/${jobId}`);
  }

  markUploadJobAsFailed(jobId: string, errorMessage?: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/auctions/upload-progress/${jobId}/mark-failed`, { error_message: errorMessage });
  }

  triggerAuctionsAnalysis(limit: number = 100): Observable<Models.AuctionTriggerResponse> {
    return this.http.post<Models.AuctionTriggerResponse>(`${this.baseUrl}/auctions/trigger-analysis?limit=${limit}`, {});
  }

  triggerBulkRankAnalysis(limit: number = 1000): Observable<Models.AuctionTriggerResponse> {
    return this.http.post<Models.AuctionTriggerResponse>(`${this.baseUrl}/auctions/trigger-bulk-rank?limit=${limit}`, {});
  }

  /**
   * Utility Methods
   */
  formatDomain(domain: string): string {
    return domain.replace(/^https?:\/\//, '').replace(/^www\./, '').toLowerCase().trim();
  }

  validateDomain(domain: string): boolean {
    const domainRegex = /^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$/;
    return domainRegex.test(domain);
  }
}
