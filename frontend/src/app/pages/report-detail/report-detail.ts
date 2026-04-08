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
    private route = inject(ActivatedRoute);
    private api = inject(ApiService);

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
    error = signal<string | null>(null);
    activeTab = signal<string>('overview');
    backlinks = signal<ReferringDomain[]>([]);
    referringDomains = signal<ReferringDomain[]>([]);
    keywords = signal<OrganicKeyword[]>([]);
    backlinksTotal = signal<number>(0);
    referringDomainsTotal = signal<number>(0);
    keywordsTotal = signal<number>(0);
    private loadedDetailTabs = new Set<string>();

    private pollingSub?: Subscription;

    ngOnInit() {
        this.route.paramMap.subscribe(params => {
            const d = params.get('domain');
            if (d) {
                this.domain.set(d);
                this.backlinks.set([]);
                this.referringDomains.set([]);
                this.keywords.set([]);
                this.backlinksTotal.set(0);
                this.referringDomainsTotal.set(0);
                this.keywordsTotal.set(0);
                this.loadedDetailTabs.clear();
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
            if (res.success && res.report) {
                this.report.set(res.report);
                this.error.set(null);

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

    async fetchReportDetails(domain: string, tab: 'keywords' | 'referring-domains' | 'backlinks') {
        try {
            const sectionMap: Record<'keywords' | 'referring-domains' | 'backlinks', string[]> = {
                'keywords': ['keywords'],
                'referring-domains': ['referring_domains'],
                'backlinks': ['backlinks'],
            };
            const res = await firstValueFrom(this.api.getReportDetails(domain, { sections: sectionMap[tab] }));

            if (tab === 'keywords') {
                this.keywords.set(res.keywords?.items || []);
                this.keywordsTotal.set(res.keywords?.total_count || 0);
            } else if (tab === 'referring-domains') {
                this.referringDomains.set(res.referring_domains?.items || []);
                this.referringDomainsTotal.set(res.referring_domains?.total_count || 0);
            } else if (tab === 'backlinks') {
                this.backlinks.set(res.backlinks?.items || []);
                this.backlinksTotal.set(res.backlinks?.total_count || 0);
            }

            this.loadedDetailTabs.add(tab);
        } catch (err) {
            console.error('Error fetching report details:', err);
        }
    }

    async reAnalyze() {
        const d = this.domain();
        if (!d) return;

        this.loading.set(true);
        this.error.set(null);

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
                    if (res.success && res.report) {
                        this.report.set(res.report);
                        this.error.set(null);
                        this.loading.set(false);
                        if (res.report.status === 'completed' && this.hasDetailedData(res.report)) {
                            this.ensureActiveTabData();
                        }
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

    ensureActiveTabData() {
        const d = this.domain();
        const tab = this.activeTab();
        if (!d || !this.hasDetailedData(this.report())) return;

        if ((tab === 'keywords' || tab === 'referring-domains' || tab === 'backlinks') && !this.loadedDetailTabs.has(tab)) {
            this.fetchReportDetails(d, tab);
        }
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
