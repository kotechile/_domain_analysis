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

  getAnalysisProgress(domain: string): Observable<Models.ProgressResponse> {
    return this.http.get<Models.ProgressResponse>(`${this.baseUrl}/reports/${domain}/progress`);
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

  triggerBulkRefresh(filters: any, force: boolean = false): Observable<{ success: boolean; message: string; triggered_count: number; cost: number }> {
    return this.http.post<{ success: boolean; message: string; triggered_count: number; cost: number }>(
      `${this.baseUrl}/auctions/bulk-refresh`,
      { filters, force }
    );
  }

  triggerForceRefresh(filters: any): Observable<{ success: boolean; message: string; triggered_count: number; cost: number }> {
    return this.http.post<{ success: boolean; message: string; triggered_count: number; cost: number }>(
      `${this.baseUrl}/auctions/force-refresh`,
      { filters }
    );
  }

  togglePreferredAuction(id: string, preferred: boolean): Observable<{ success: boolean }> {
    return this.http.post<{ success: boolean }>(
      `${this.baseUrl}/auctions/${id}/preferred`,
      { preferred }
    );
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
