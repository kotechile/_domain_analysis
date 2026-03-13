import { Component, inject, signal, computed, effect, OnDestroy, OnInit } from '@angular/core';
import { CommonModule, TitleCasePipe, DatePipe, DecimalPipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../services/api';
import { LucideAngularModule, ArrowLeft, RefreshCw, Download, Sparkles, TrendingUp, History, ShieldCheck, Globe, Zap, AlertTriangle, CheckCircle, Search, Info, Flag, Target, Lightbulb } from 'lucide-angular';
import { firstValueFrom, interval, Subscription, startWith, switchMap, takeWhile } from 'rxjs';
import { DomainAnalysisReport } from '../../models/domain.model';

@Component({
    selector: 'app-report-detail',
    standalone: true,
    imports: [CommonModule, RouterLink, LucideAngularModule, TitleCasePipe, DatePipe, DecimalPipe],
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

    // State
    domain = signal<string | null>(null);
    report = signal<DomainAnalysisReport | null>(null);
    loading = signal<boolean>(true);
    error = signal<string | null>(null);
    activeTab = signal<string>('overview');

    private pollingSub?: Subscription;

    ngOnInit() {
        this.route.paramMap.subscribe(params => {
            const d = params.get('domain');
            if (d) {
                this.domain.set(d);
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

                // Stop polling if completed or failed
                if (res.report.status === 'completed' || res.report.status === 'failed') {
                    this.stopPolling();
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
}
