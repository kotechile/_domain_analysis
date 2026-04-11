import { Component, inject, signal, computed, effect, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { CommonModule, TitleCasePipe, DatePipe, DecimalPipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../services/api';
import { LucideAngularModule, ArrowLeft, RefreshCw, Download, Sparkles, TrendingUp, History, ShieldCheck, Globe, Zap, AlertTriangle, CheckCircle, Search, Info, Flag, Target, Lightbulb, BarChart3, Link2 } from 'lucide-angular';
import { firstValueFrom, interval, Subscription, startWith, switchMap, takeWhile } from 'rxjs';
import { DomainAnalysisReport, OrganicKeyword, ReferringDomain } from '../../models/domain.model';
import { TrafficChartComponent } from '../../components/traffic-chart/traffic-chart';

@Component({
    selector: 'app-report-detail',
    standalone: true,
    imports: [CommonModule, RouterLink, LucideAngularModule, DatePipe, DecimalPipe, TrafficChartComponent],
    templateUrl: './report-detail.html',
    styles: [`
    .report-card {
      @apply rounded-3xl border border-opacity-10 backdrop-blur-md transition-all duration-500;
      border-color: var(--border-color);
      background: var(--card-bg);
    }
    .metric-bubble {
      @apply p-6 rounded-2xl flex flex-col items-center justify-center space-y-2 text-center border border-opacity-5;
      background: rgba(var(--accent-color-rgb), 0.03);
      border-color: var(--border-color);
    }
    .status-badge {
      @apply px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest flex items-center space-x-2;
    }
    .tab-btn {
      @apply px-6 py-4 text-sm font-bold opacity-40 transition-all border-b-2 border-transparent flex items-center space-x-2;
      color: var(--text-color);
    }
    .tab-btn.active {
      @apply opacity-100;
      border-color: var(--accent-color);
      color: var(--accent-color);
    }
    .ai-bubble {
      @apply p-6 rounded-2xl border border-opacity-20 space-y-4;
      border-color: var(--accent-color);
      background: linear-gradient(135deg, rgba(var(--accent-color-rgb), 0.05) 0%, transparent 100%);
    }
  `]
})
export class ReportDetailComponent implements OnInit, OnDestroy {
    private readonly initialDetailLimit = 25;
    private readonly detailPageSize = 25;
    private route = inject(ActivatedRoute);
    private api = inject(ApiService);
    private summaryMetricsRequested = false;

    // Icons
    readonly ArrowLeft = ArrowLeft;
    readonly RefreshCw = RefreshCw;
    readonly Download = Download;
    readonly Sparkles = Sparkles;
    readonly TrendingUp = TrendingUp;
    readonly History = History;
    readonly ShieldCheck = ShieldCheck;
    readonly Globe = Globe;
    readonly Zap = Zap;
    readonly AlertTriangle = AlertTriangle;
    readonly CheckCircle = CheckCircle;
    readonly Search = Search;
    readonly Info = Info;
    readonly Flag = Flag;
    readonly Target = Target;
    readonly Lightbulb = Lightbulb;
    readonly BarChart3 = BarChart3;
    readonly Link2 = Link2;

    // State
    domain = signal<string | null>(null);
    report = signal<DomainAnalysisReport | null>(null);
    loading = signal<boolean>(true);
    downloadingReport = signal<boolean>(false);
    error = signal<string | null>(null);
    activeTab = signal<string>('overview');
    backlinks = signal<ReferringDomain[]>([]);
    referringDomains = signal<ReferringDomain[]>([]);
    keywords = signal<OrganicKeyword[]>([]);
    backlinksTotal = signal<number>(0);
    referringDomainsTotal = signal<number>(0);
    keywordsTotal = signal<number>(0);
    detailLoading = signal<Record<string, boolean>>({
        'keywords': false,
        'referring-domains': false,
        'backlinks': false,
    });
    private loadedDetailTabs = new Set<string>();

    private pollingSub?: Subscription;

    ngOnInit() {
        this.route.paramMap.subscribe(params => {
            const d = params.get('domain');
            if (d) {
                this.domain.set(d);
                this.report.set(null);
                this.error.set(null);
                this.loading.set(true);
                this.backlinks.set([]);
                this.referringDomains.set([]);
                this.keywords.set([]);
                this.backlinksTotal.set(0);
                this.referringDomainsTotal.set(0);
                this.keywordsTotal.set(0);
                this.loadedDetailTabs.clear();
                this.summaryMetricsRequested = false;
                this.startPolling(d);
            }
        });
    }

    ngOnDestroy() {
        this.stopPolling();
    }

    async fetchReport(force: boolean = false) {
        if (force) this.loading.set(true);
        const d = this.domain();
        if (!d) return;

        try {
            const res = await firstValueFrom(this.api.getReport(d));
            if (res.report) {
                this.report.set(res.report);
                this.error.set(res.success ? null : (res.message || null));
                await this.ensureSummaryMetrics(res.report);

                // Start polling if it's in progress
                if (res.report.status === 'pending' || res.report.status === 'in_progress') {
                    this.startPolling(d);
                }
            } else {
                this.error.set(res.message || 'Failed to fetch report');
            }
        } catch (err) {
            console.error('Error fetching report:', err);
            this.error.set('Connection error. Please try again.');
        } finally {
            this.loading.set(false);
        }
    }

    async fetchReportDetails(domain: string, tab: 'keywords' | 'referring-domains' | 'backlinks', append: boolean = false) {
        const currentCount = tab === 'keywords'
            ? this.keywords().length
            : tab === 'referring-domains'
                ? this.referringDomains().length
                : this.backlinks().length;

        this.detailLoading.update(state => ({ ...state, [tab]: true }));

        try {
            const sectionMap: Record<'keywords' | 'referring-domains' | 'backlinks', string[]> = {
                'keywords': ['keywords'],
                'referring-domains': ['referring_domains'],
                'backlinks': ['backlinks'],
            };
            const res = await firstValueFrom(this.api.getReportDetails(domain, {
                sections: sectionMap[tab],
                keywordsLimit: tab === 'keywords' ? this.detailPageSize : this.initialDetailLimit,
                backlinksLimit: tab === 'keywords' ? this.initialDetailLimit : this.detailPageSize,
                keywordsOffset: tab === 'keywords' && append ? currentCount : 0,
                backlinksOffset: tab !== 'keywords' && append ? currentCount : 0,
            }));

            if (tab === 'keywords') {
                this.keywords.set(append ? [...this.keywords(), ...(res.keywords?.items || [])] : (res.keywords?.items || []));
                this.keywordsTotal.set(res.keywords?.total_count || 0);
            } else if (tab === 'referring-domains') {
                this.referringDomains.set(append ? [...this.referringDomains(), ...(res.referring_domains?.items || [])] : (res.referring_domains?.items || []));
                this.referringDomainsTotal.set(res.referring_domains?.total_count || 0);
            } else if (tab === 'backlinks') {
                this.backlinks.set(append ? [...this.backlinks(), ...(res.backlinks?.items || [])] : (res.backlinks?.items || []));
                this.backlinksTotal.set(res.backlinks?.total_count || 0);
            }

            const currentReport = this.report();
            if (currentReport?.data_for_seo_metrics) {
                if ((res.backlinks?.total_count || 0) > (currentReport.data_for_seo_metrics.total_backlinks || 0)) {
                    currentReport.data_for_seo_metrics.total_backlinks = res.backlinks?.total_count || 0;
                }
                if ((res.referring_domains?.total_count || 0) > (currentReport.data_for_seo_metrics.total_referring_domains || 0)) {
                    currentReport.data_for_seo_metrics.total_referring_domains = res.referring_domains?.total_count || 0;
                }
                if ((res.keywords?.total_count || 0) > (currentReport.data_for_seo_metrics.total_keywords || 0)) {
                    currentReport.data_for_seo_metrics.total_keywords = res.keywords?.total_count || 0;
                }
                this.report.set({ ...currentReport });
            }

            const needsHydratedRefresh =
                tab === 'backlinks' &&
                (res.backlinks?.total_count || 0) > 0 &&
                (
                    (currentReport?.llm_analysis?.confidence_score || 0) <= 0.01 ||
                    (currentReport?.data_for_seo_metrics?.total_backlinks || 0) === 0
                );

            if (needsHydratedRefresh) {
                await this.fetchReport();
            }

            this.loadedDetailTabs.add(tab);
        } catch (err) {
            console.error('Error fetching report details:', err);
        } finally {
            this.detailLoading.update(state => ({ ...state, [tab]: false }));
        }
    }

    async reAnalyze() {
        const d = this.domain();
        if (!d) return;

        this.loading.set(true);
        this.error.set(null);
        this.loadedDetailTabs.clear();

        try {
            // Trigger fresh analysis
            const res = await firstValueFrom(this.api.analyzeDomain(d, 'dual'));
            if (res.success) {
                // If successful, start polling for the new analysis
                this.startPolling(d);
            } else {
                this.error.set(res.message || 'Failed to start re-analysis');
                this.loading.set(false);
            }
        } catch (err: any) {
            console.error('Error starting re-analysis:', err);
            // Handle 402 Insufficient credits specifically
            if (err.status === 402) {
                this.error.set('Insufficient credits to re-analyze this domain.');
            } else {
                this.error.set('Failed to start re-analysis. Please check your credit balance.');
            }
            this.loading.set(false);
        }
    }

    async downloadReport() {
        const d = this.domain();
        if (!d || this.downloadingReport()) return;

        this.downloadingReport.set(true);
        try {
            const blob = await firstValueFrom(this.api.downloadExecutivePdf(d));
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `${d}-executive-report.pdf`;
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            setTimeout(() => {
                window.URL.revokeObjectURL(url);
                link.remove();
            }, 0);
        } catch (err) {
            console.error('Error downloading report:', err);
            this.error.set('Failed to download report. Please try again.');
        } finally {
            this.downloadingReport.set(false);
        }
    }

    startPolling(domain: string) {
        this.stopPolling();
        this.loading.set(true);

        this.pollingSub = interval(3000)
            .pipe(
                startWith(0),
                switchMap(() => this.api.getReport(domain)),
                takeWhile(res => {
                    const status = res.report?.status;
                    return status === 'pending' || status === 'in_progress' || !res.report;
                }, true) // true means return the last value that failed the predicate
            )
            .subscribe({
                next: (res) => {
                    if (res.report) {
                        this.report.set(res.report);
                        this.error.set(res.success ? null : (res.message || null));
                        this.loading.set(false);
                        if (res.report.status === 'completed') {
                            void this.ensureSummaryMetrics(res.report).finally(() => {
                                if (this.hasDetailedData(res.report!)) {
                                    this.ensureActiveTabData();
                                }
                            });
                        }
                    } else {
                        this.loading.set(true);
                    }
                },
                error: (err) => {
                    console.error('Polling error:', err);
                    this.error.set('Real-time updates failed.');
                    this.loading.set(false);
                }
            });
    }

    stopPolling() {
        if (this.pollingSub) {
            this.pollingSub.unsubscribe();
        }
    }

    setTab(tab: string) {
        this.activeTab.set(tab);
        this.ensureActiveTabData();
    }

    private async ensureSummaryMetrics(report: DomainAnalysisReport) {
        if (this.summaryMetricsRequested || report.status !== 'completed') return;

        const hasMissingToplineMetrics =
            (report.data_for_seo_metrics?.total_backlinks || 0) === 0 ||
            (report.data_for_seo_metrics?.total_referring_domains || 0) === 0;

        if (!hasMissingToplineMetrics) return;

        const d = this.domain();
        if (!d) return;

        this.summaryMetricsRequested = true;

        try {
            const res = await firstValueFrom(this.api.getReportDetails(d, {
                sections: ['backlinks', 'referring_domains', 'keywords'],
                backlinksLimit: 1,
                keywordsLimit: 1,
            }));

            const currentReport = this.report();
            if (!currentReport?.data_for_seo_metrics) return;

            currentReport.data_for_seo_metrics.total_backlinks = Math.max(
                currentReport.data_for_seo_metrics.total_backlinks || 0,
                res.backlinks?.total_count || 0,
            );
            currentReport.data_for_seo_metrics.total_referring_domains = Math.max(
                currentReport.data_for_seo_metrics.total_referring_domains || 0,
                res.referring_domains?.total_count || 0,
            );
            currentReport.data_for_seo_metrics.total_keywords = Math.max(
                currentReport.data_for_seo_metrics.total_keywords || 0,
                res.keywords?.total_count || 0,
            );

            this.backlinksTotal.set(res.backlinks?.total_count || this.backlinksTotal());
            this.referringDomainsTotal.set(res.referring_domains?.total_count || this.referringDomainsTotal());
            this.keywordsTotal.set(res.keywords?.total_count || this.keywordsTotal());
            this.report.set({ ...currentReport });
        } catch (err) {
            console.error('Error hydrating summary metrics:', err);
            this.summaryMetricsRequested = false;
        }
    }

    ensureActiveTabData() {
        const d = this.domain();
        const tab = this.activeTab();
        const report = this.report();
        if (!d || !report || report.status !== 'completed') return;

        if ((tab === 'keywords' || tab === 'referring-domains' || tab === 'backlinks') && !this.loadedDetailTabs.has(tab)) {
            this.fetchReportDetails(d, tab);
        }
    }

    async loadMore(tab: 'keywords' | 'referring-domains' | 'backlinks') {
        const d = this.domain();
        if (!d || !this.canLoadMore(tab) || this.detailLoading()[tab]) return;
        await this.fetchReportDetails(d, tab, true);
    }

    canLoadMore(tab: 'keywords' | 'referring-domains' | 'backlinks'): boolean {
        if (tab === 'keywords') return this.keywords().length < this.keywordsTotal();
        if (tab === 'referring-domains') return this.referringDomains().length < this.referringDomainsTotal();
        return this.backlinks().length < this.backlinksTotal();
    }

    remainingCount(tab: 'keywords' | 'referring-domains' | 'backlinks'): number {
        if (tab === 'keywords') return Math.max(this.keywordsTotal() - this.keywords().length, 0);
        if (tab === 'referring-domains') return Math.max(this.referringDomainsTotal() - this.referringDomains().length, 0);
        return Math.max(this.backlinksTotal() - this.backlinks().length, 0);
    }

    getBuyColor(rec: string | undefined): string {
        if (!rec) return 'gray';
        if (rec.includes('BUY')) return '#10b981';
        if (rec.includes('CAUTION')) return '#f59e0b';
        return '#ef4444';
    }

    // Formatting helpers
    formatNumber(val: number | undefined): string {
        return val ? val.toLocaleString() : '0';
    }

    formatProgressLabel(value: string | undefined | null): string {
        if (!value) return 'Analyzing Core DNA';
        return value
            .replace(/_/g, ' ')
            .replace(/\b\w/g, (char) => char.toUpperCase());
    }

    getProgressUpdates(): string[] {
        const progress = this.report()?.progress_data;
        if (!progress) return [];

        const completed = progress.completed_operations || [];
        if (completed.length) {
            return completed.map(step => this.formatProgressLabel(step));
        }

        if (progress.current_operation) {
            return [`Current stage: ${this.formatProgressLabel(progress.current_operation)}`];
        }

        return ['Analysis request accepted and queued'];
    }

    getKeywordLabel(kw: OrganicKeyword): string {
        return kw.keyword || kw.keyword_data?.keyword || 'Unknown keyword';
    }

    getKeywordPosition(kw: OrganicKeyword): number {
        return kw.rank || kw.ranked_serp_element?.serp_item?.rank_absolute || 0;
    }

    getKeywordSearchVolume(kw: OrganicKeyword): number {
        return kw.search_volume || kw.keyword_data?.keyword_info?.search_volume || 0;
    }

    getKeywordDifficulty(kw: OrganicKeyword): number {
        return kw.keyword_difficulty || kw.keyword_data?.keyword_properties?.keyword_difficulty || 0;
    }

    getKeywordCpc(kw: OrganicKeyword): number {
        return kw.cpc || kw.keyword_data?.keyword_info?.cpc || 0;
    }

    getKeywordUrl(kw: OrganicKeyword): string {
        return kw.url || kw.ranked_serp_element?.serp_item?.url || '';
    }

    hasDetailedData(report: DomainAnalysisReport | null): boolean {
        if (!report?.detailed_data_available) return false;
        return Boolean(report.detailed_data_available.backlinks || report.detailed_data_available.keywords);
    }

    // Traffic chart helpers
    getLatestTraffic(): number {
        const traffic = this.report()?.historical_data?.rank_overview?.organic_traffic;
        if (!traffic?.length) return 0;
        const sorted = [...traffic].sort((a, b) =>
            new Date(b.date).getTime() - new Date(a.date).getTime()
        );
        return sorted[0]?.value || 0;
    }

    getPeakTraffic(): number {
        const traffic = this.report()?.historical_data?.rank_overview?.organic_traffic;
        if (!traffic?.length) return 0;
        return Math.max(...traffic.map(t => t.value));
    }
}
