import { Component, inject, signal, computed, effect, OnInit, untracked, OnDestroy } from '@angular/core';
import { CommonModule, TitleCasePipe, DatePipe, DecimalPipe } from '@angular/common';
import { RouterLink, ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api';
import { LucideAngularModule, Filter, ArrowUpDown, ArrowUp, ArrowDown, ExternalLink, Sparkles, TrendingUp, History, ShieldCheck, Star, Target, Menu, X } from 'lucide-angular';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { CreditService } from '../../services/credit';
import { firstValueFrom, interval, Subscription } from 'rxjs';
import { switchMap, takeWhile, take } from 'rxjs/operators';
import { Auction } from '../../models/domain.model';

@Component({
  selector: 'app-marketplace',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideAngularModule, DatePipe, MatSnackBarModule],
  templateUrl: './marketplace.html',
  styles: [`
    .table-container {
      @apply rounded-2xl border border-opacity-10 w-full overflow-auto max-h-[75vh];
      border-color: var(--border-color);
      background: var(--card-bg);
    }
    
    th {
      @apply px-4 py-4 text-left text-xs font-bold uppercase tracking-widest opacity-40;
      color: var(--text-color);
    }

    td {
      @apply px-4 py-4 text-sm font-medium border-t border-opacity-5;
      border-color: var(--border-color);
      color: var(--text-color);
      font-variant-numeric: tabular-nums;
    }

    tr:hover td {
      background-color: rgb(var(--accent-color-rgb) / 0.08);
      color: var(--text-color) !important;
    }

    tr {
      @apply transition-colors duration-200;
    }

    tr:hover span, tr:hover div {
      color: var(--text-color) !important;
    }

    .favorite-btn {
      @apply p-1.5 rounded-lg transition-all active:scale-95 text-gray-400 hover:text-amber-500 hover:bg-amber-500/10;
    }
    .favorite-active {
      @apply text-amber-500 bg-amber-500/10;
    }

    .sort-active {
      @apply opacity-100;
      color: var(--accent-color);
    }

    .metric-pill {
      @apply px-2.5 py-1 rounded-lg text-sm font-semibold flex items-center space-x-1.5 min-w-[50px] justify-center;
      background: rgba(var(--accent-color-rgb, 13, 110, 253), 0.1);
      color: var(--accent-color);
    }
    
    .platform-pill {
      @apply px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all active:scale-95 shadow-sm hover:shadow-md cursor-pointer border border-opacity-10;
    }

    .platform-godaddy { background: #1b1b1b; color: #00d290; border-color: #00d29033; }
    .platform-dynadot { background: #fdf2f2; color: #e11d48; border-color: #e11d4833; }
    .platform-namecheap { background: #fff7ed; color: #c2410c; border-color: #c2410c33; }
    .platform-sedo { background: #eff6ff; color: #1d4ed8; border-color: #1d4ed833; }
    .platform-namesilo { background: #f0fdf4; color: #15803d; border-color: #15803d33; }
    .platform-default { background: var(--card-bg); color: var(--text-color); border-color: var(--border-color); }
    
  `]
})
export class MarketplaceComponent implements OnInit, OnDestroy {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private filtersHydrated = false;
  private fetchTimeout: ReturnType<typeof setTimeout> | null = null;

  // Icons
  readonly Filter = Filter;
  readonly ArrowUpDown = ArrowUpDown;
  readonly ArrowUp = ArrowUp;
  readonly ArrowDown = ArrowDown;
  readonly ExternalLink = ExternalLink;
  readonly Sparkles = Sparkles;
  readonly TrendingUp = TrendingUp;
  readonly History = History;
  readonly ShieldCheck = ShieldCheck;
  readonly Star = Star;
  readonly Target = Target;
  readonly Menu = Menu;
  readonly X = X;

  // State Signals
  auctions = signal<Auction[]>([]);
  loading = signal<boolean>(true);
  totalCount = signal<number>(0);

  // Background processing state
  fillGapsInProgress = signal<boolean>(false);
  fillGapsJobId = signal<string | null>(null);
  fillGapsProgress = signal<{ percent: number; message: string } | null>(null);
  private fillGapsStartedAt = signal<number | null>(null);

  forceRefreshInProgress = signal<boolean>(false);
  forceRefreshJobId = signal<string | null>(null);
  forceRefreshProgress = signal<{ percent: number; message: string } | null>(null);
  private forceRefreshStartedAt = signal<number | null>(null);
  postRefreshSyncInProgress = signal<boolean>(false);
  postRefreshSyncProgress = signal<{ percent: number; message: string } | null>(null);
  private postRefreshSyncStartedAt = signal<number | null>(null);
  private progressClock = signal<number>(Date.now());

  private progressSubscriptions = new Map<string, Subscription>();
  private postRefreshSyncSubscription: Subscription | null = null;
  private progressClockSubscription: Subscription | null = null;
  private notFoundCount = new Map<string, number>(); // Track 404 errors per job

  // Filter Signals
  sortBy = signal<string>('expiration_date');
  sortOrder = signal<'asc' | 'desc'>('asc');
  preferredOnly = signal<boolean>(false);
  scoredOnly = signal<boolean>(false);
  statisticsOnly = signal<boolean>(false);

  // Advanced Filters
  minScore = signal<number | null>(null);
  maxScore = signal<number | null>(null);
  selectedPlatforms = signal<string[]>([]);
  selectedTlds = signal<string[]>([]);
  offeringType = signal<string>(''); // 'auction', 'buy_now', 'backorder'
  showFilters = signal<boolean>(false);
  showMobileActions = signal<boolean>(false);
  availableTlds = signal<string[]>([]);
  readonly commonTlds = ['.com', '.net', '.ai', '.org', '.io', '.co', '.app', '.dev'];

  // Date Filters (Empty by default to show all results)
  expirationFromDate = signal<string>('');
  expirationToDate = signal<string>('');

  limit = signal<number>(50);
  offset = signal<number>(0);

  activeFilterCount = computed(() => {
    let count = 0;
    if (this.preferredOnly()) count++;
    if (this.scoredOnly()) count++;
    if (this.statisticsOnly()) count++;
    if (this.minScore() !== null && this.minScore() !== undefined) count++;
    if (this.maxScore() !== null && this.maxScore() !== undefined) count++;
    if (this.selectedPlatforms().length > 0) count++;
    if (this.selectedTlds().length > 0) count++;
    if (this.offeringType()) count++;
    if (this.expirationFromDate() || this.expirationToDate()) count++;
    return count;
  });

  otherTlds = computed(() => this.availableTlds().filter(tld => !this.commonTlds.includes(tld)));

  allOtherTldsSelected = computed(() => {
    const others = this.otherTlds();
    return others.length > 0 && others.every(tld => this.selectedTlds().includes(tld));
  });

  fillGapsDisplayPercent = computed(() => {
    this.progressClock();
    if (!this.fillGapsInProgress()) return 0;
    return this.getStagedPercent(this.fillGapsStartedAt(), 75, 120000);
  });

  forceRefreshDisplayPercent = computed(() => {
    this.progressClock();
    if (!this.forceRefreshInProgress()) return 0;
    return this.getStagedPercent(this.forceRefreshStartedAt(), 75, 120000);
  });

  postRefreshSyncDisplayPercent = computed(() => {
    this.progressClock();
    if (!this.postRefreshSyncInProgress()) return 0;
    return 75 + this.getStagedPercent(this.postRefreshSyncStartedAt(), 24, 90000);
  });

  private snackBar = inject(MatSnackBar);
  private creditService = inject(CreditService);

  constructor() {
    effect(() => {
      this.sortBy();
      this.sortOrder();
      this.preferredOnly();
      this.scoredOnly();
      this.statisticsOnly();
      this.minScore();
      this.maxScore();
      this.selectedPlatforms();
      this.selectedTlds();
      this.offeringType();
      this.expirationFromDate();
      this.expirationToDate();
      this.limit();
      this.offset();

      if (!this.filtersHydrated) {
        return;
      }

      this.scheduleFetchAuctions();
    });
  }

  private getNormalizedExpirationRange(fromValue: string, toValue: string) {
    const from = fromValue || '';
    const to = toValue || '';

    if (from && to && from > to) {
      return {
        from: to,
        to: from,
      };
    }

    return { from, to };
  }

  private setExpirationRange(fromValue: string, toValue: string) {
    const normalized = this.getNormalizedExpirationRange(fromValue, toValue);
    this.expirationFromDate.set(normalized.from);
    this.expirationToDate.set(normalized.to);
  }

  private scheduleFetchAuctions() {
    if (this.fetchTimeout) {
      clearTimeout(this.fetchTimeout);
    }

    this.fetchTimeout = setTimeout(() => {
      this.fetchTimeout = null;
      this.fetchAuctions();
    }, 0);
  }

  private normalizeExpirationRange(changedField: 'from' | 'to', rawValue: string) {
    const nextValue = rawValue || '';
    const fromValue = changedField === 'from' ? nextValue : this.expirationFromDate();
    const toValue = changedField === 'to' ? nextValue : this.expirationToDate();

    this.setExpirationRange(fromValue, toValue);
    this.offset.set(0);
  }

  ngOnDestroy() {
    // Clean up progress polling subscriptions
    this.progressSubscriptions.forEach(sub => sub.unsubscribe());
    this.progressSubscriptions.clear();
    this.stopPostRefreshSync();
    this.stopProgressClock();
    if (this.fetchTimeout) {
      clearTimeout(this.fetchTimeout);
      this.fetchTimeout = null;
    }
  }

  private startProgressClock() {
    if (this.progressClockSubscription) return;
    this.progressClockSubscription = interval(1000).subscribe(() => {
      this.progressClock.set(Date.now());
    });
  }

  private stopProgressClock() {
    if (this.progressClockSubscription) {
      this.progressClockSubscription.unsubscribe();
      this.progressClockSubscription = null;
    }
  }

  private refreshProgressClockState() {
    if (this.fillGapsInProgress() || this.forceRefreshInProgress() || this.postRefreshSyncInProgress()) {
      this.startProgressClock();
    } else {
      this.stopProgressClock();
    }
  }

  private getStagedPercent(startedAt: number | null, maxPercent: number, durationMs: number): number {
    if (!startedAt) return 0;
    const elapsed = Math.max(0, this.progressClock() - startedAt);
    return Math.min(maxPercent, Math.round((elapsed / durationMs) * maxPercent));
  }

  getFillStageMessage(): string {
    const raw = this.fillGapsProgress()?.message || 'Preparing provider requests...';
    if ((this.fillGapsProgress()?.percent || 0) >= 100) {
      return 'Provider work is queued. Waiting for external metrics and callback processing before the table is fully updated.';
    }
    return raw;
  }

  getForceRefreshStageMessage(): string {
    const raw = this.forceRefreshProgress()?.message || 'Preparing provider requests...';
    if ((this.forceRefreshProgress()?.percent || 0) >= 100) {
      return 'Provider work is queued. Waiting for fresh callbacks before the table is fully updated.';
    }
    return raw;
  }

  private stopPostRefreshSync() {
    if (this.postRefreshSyncSubscription) {
      this.postRefreshSyncSubscription.unsubscribe();
      this.postRefreshSyncSubscription = null;
    }
    this.postRefreshSyncInProgress.set(false);
    this.postRefreshSyncProgress.set(null);
    this.postRefreshSyncStartedAt.set(null);
    this.refreshProgressClockState();
  }

  private startPostRefreshSync(type: 'fill_gaps' | 'force_refresh', statusMessage?: string) {
    const label = type === 'fill_gaps' ? 'Fill Metrics' : 'Force Refresh';
    const totalPasses = 6;
    let completedPasses = 0;

    this.stopPostRefreshSync();
    this.postRefreshSyncInProgress.set(true);
    this.postRefreshSyncStartedAt.set(Date.now());
    this.postRefreshSyncProgress.set({
      percent: 75,
      message: statusMessage || `${label} finished queuing requests. Metrics are still syncing into the table...`
    });
    this.refreshProgressClockState();

    this.fetchAuctions();
    this.creditService.refreshData();

    this.postRefreshSyncSubscription = interval(10000)
      .pipe(take(totalPasses))
      .subscribe({
        next: () => {
          completedPasses += 1;
          const percent = Math.round((completedPasses / totalPasses) * 100);
          this.fetchAuctions();
          this.postRefreshSyncProgress.set({
            percent: 75 + Math.round((completedPasses / totalPasses) * 24),
            message: `${label} results are still arriving from providers. Refreshing table automatically (${completedPasses}/${totalPasses})...`
          });
        },
        error: () => {
          this.stopPostRefreshSync();
        },
        complete: () => {
          this.fetchAuctions();
          this.stopPostRefreshSync();
          this.snackBar.open(
            `${label} sync window finished. If a few rows are still blank, provider callbacks may still be arriving.`,
            'Close',
            { duration: 6000 }
          );
        }
      });
  }

  /**
   * Start polling for job progress
   */
  private startProgressPolling(jobId: string, type: 'fill_gaps' | 'force_refresh') {
    // Stop any existing polling for this job
    this.stopProgressPolling(jobId);

    // Poll every 5 seconds (increased from 3 to reduce server load)
    const sub = interval(5000)
      .pipe(
        switchMap(() => this.api.getRefreshStatus(jobId)),
        takeWhile((status: any) => {
          // Continue polling while running, but also let completed/failed through
          return status?.status === 'running';
        }, true),
        // Stop after 5 minutes (60 polls * 5 seconds) to prevent infinite polling
        take(60)
      )
      .subscribe({
        next: (status: any) => {
          if (!status) {
            console.warn('No status returned from API');
            return;
          }

          const progress = {
            percent: status.progress_percent || 0,
            message: status.message || 'Processing...'
          };

          if (type === 'fill_gaps') {
            this.fillGapsProgress.set(progress);
          } else {
            this.forceRefreshProgress.set(progress);
          }

          // If completed, stop polling and refresh
          if (status.status === 'completed' || status.status === 'failed') {
            this.stopProgressPolling(jobId);

            if (type === 'fill_gaps') {
              this.fillGapsInProgress.set(false);
              this.fillGapsJobId.set(null);
              this.fillGapsStartedAt.set(null);
              const msg = status.status === 'completed'
                ? `✅ ${status.message || 'Fill Gaps completed!'}`
                : `❌ ${status.message || 'Fill Gaps failed'}`;
              this.snackBar.open(msg, 'Close', { duration: 8000 });
            } else {
              this.forceRefreshInProgress.set(false);
              this.forceRefreshJobId.set(null);
              this.forceRefreshStartedAt.set(null);
              const msg = status.status === 'completed'
                ? `✅ ${status.message || 'Force Refresh completed!'}`
                : `❌ ${status.message || 'Force Refresh failed'}`;
              this.snackBar.open(msg, 'Close', { duration: 8000 });
            }

            this.startPostRefreshSync(type, status.message);
          }
        },
        error: (err) => {
          console.error('Progress polling error:', err);

          // Track 404 errors - if we get too many, assume job completed and refresh
          if (err.status === 404) {
            const currentCount = this.notFoundCount.get(jobId) || 0;
            this.notFoundCount.set(jobId, currentCount + 1);

            // After 3 consecutive 404s, assume job is done and refresh
            if (currentCount >= 3) {
              console.log('Assuming job completed after multiple 404s, refreshing data');
              this.stopProgressPolling(jobId);
              this.notFoundCount.delete(jobId);

              if (type === 'fill_gaps') {
                this.fillGapsInProgress.set(false);
                this.fillGapsJobId.set(null);
                this.fillGapsProgress.set(null);
                this.fillGapsStartedAt.set(null);
                this.snackBar.open('✅ Fill Metrics likely finished queuing. Keeping the table syncing for a minute...', 'Close', { duration: 5000 });
              } else {
                this.forceRefreshInProgress.set(false);
                this.forceRefreshJobId.set(null);
                this.forceRefreshProgress.set(null);
                this.forceRefreshStartedAt.set(null);
                this.snackBar.open('✅ Force Refresh likely finished queuing. Keeping the table syncing for a minute...', 'Close', { duration: 5000 });
              }

              this.startPostRefreshSync(type);
            }
            return; // Continue polling
          }

          // Clear notFoundCount on non-404 error
          this.notFoundCount.delete(jobId);
          this.stopProgressPolling(jobId);

          // Clear state for real errors
          if (type === 'fill_gaps') {
            this.fillGapsInProgress.set(false);
            this.fillGapsJobId.set(null);
            this.fillGapsProgress.set(null);
            this.fillGapsStartedAt.set(null);
          } else {
            this.forceRefreshInProgress.set(false);
            this.forceRefreshJobId.set(null);
            this.forceRefreshProgress.set(null);
            this.forceRefreshStartedAt.set(null);
          }
          this.refreshProgressClockState();
        },
        complete: () => {
          // Polling completed naturally (max polls reached)
          console.log('Progress polling completed (max duration reached)');
          this.stopProgressPolling(jobId);

          // Clear the progress state
          if (type === 'fill_gaps') {
            this.fillGapsInProgress.set(false);
            this.fillGapsJobId.set(null);
            this.fillGapsProgress.set(null);
            this.fillGapsStartedAt.set(null);
          } else {
            this.forceRefreshInProgress.set(false);
            this.forceRefreshJobId.set(null);
            this.forceRefreshProgress.set(null);
            this.forceRefreshStartedAt.set(null);
          }
          this.refreshProgressClockState();
        }
      });

    this.progressSubscriptions.set(jobId, sub);
  }

  /**
   * Stop polling for a specific job
   */
  private stopProgressPolling(jobId: string) {
    const sub = this.progressSubscriptions.get(jobId);
    if (sub) {
      sub.unsubscribe();
      this.progressSubscriptions.delete(jobId);
    }
  }

  ngOnInit() {
    // Sync signals from URL query parameters on initial load so filters persist across refreshes
    const qp = this.route.snapshot.queryParams;

    if (qp['sort']) this.sortBy.set(qp['sort']);
    if (qp['order']) this.sortOrder.set(qp['order'] as 'asc' | 'desc');
    if (qp['preferred']) this.preferredOnly.set(qp['preferred'] === 'true');
    if (qp['scored']) this.scoredOnly.set(qp['scored'] === 'true');
    if (qp['has_statistics']) this.statisticsOnly.set(qp['has_statistics'] === 'true');
    if (qp['min_score']) this.minScore.set(Number(qp['min_score']));
    if (qp['max_score']) this.maxScore.set(Number(qp['max_score']));
    if (qp['platforms']) this.selectedPlatforms.set(qp['platforms'].split(','));
    if (qp['tlds']) this.selectedTlds.set(qp['tlds'].split(',').filter(Boolean));
    if (qp['offering_type']) this.offeringType.set(qp['offering_type']);
    this.setExpirationRange(qp['exp_from'] || '', qp['exp_to'] || '');

    this.filtersHydrated = true;
    this.loadAvailableTlds();
    this.scheduleFetchAuctions();
  }

  async loadAvailableTlds() {
    try {
      const response = await firstValueFrom(this.api.getAuctionTlds());
      this.availableTlds.set(response.tlds || []);
    } catch (error) {
      console.error('Failed to load auction TLDs:', error);
      this.availableTlds.set(this.commonTlds);
    }
  }

  onExpirationFromDateChange(value: string) {
    this.normalizeExpirationRange('from', value);
  }

  onExpirationToDateChange(value: string) {
    this.normalizeExpirationRange('to', value);
  }

  async triggerBulkRefresh() {
    // Prevent duplicate requests
    if (this.fillGapsInProgress()) {
      this.snackBar.open('⏳ Fill Gaps is already running…', 'Close', { duration: 3000 });
      return;
    }

    // Build the exact same filter set that the table currently uses
    const filters: Record<string, any> = {};

    if (this.preferredOnly()) filters['preferred'] = true;
    if (this.scoredOnly()) filters['scored'] = true;
    if (this.statisticsOnly()) filters['has_statistics'] = true;
    if (this.expirationFromDate()) filters['expiration_from_date'] = this.expirationFromDate();
    if (this.expirationToDate()) filters['expiration_to_date'] = this.expirationToDate();
    if (this.selectedPlatforms().length) filters['auction_sites'] = this.selectedPlatforms();
    if (this.selectedTlds().length) filters['tlds'] = this.selectedTlds();
    if (this.offeringType()) filters['offering_type'] = this.offeringType();
    if (this.minScore() !== null) filters['min_score'] = this.minScore();
    if (this.maxScore() !== null) filters['max_score'] = this.maxScore();

    // Include sort context so the top 1,000 domains refreshed match the top 1,000 domains in table
    const payload = {
      filters,
      sort_by: this.sortBy(),
      sort_order: this.sortOrder()
    };

    // Set processing state
    this.fillGapsInProgress.set(true);
    this.fillGapsStartedAt.set(Date.now());
    this.fillGapsProgress.set({ percent: 0, message: 'Starting...' });
    this.refreshProgressClockState();

    // Show immediate feedback (dismiss after 3 seconds, processing continues in background)
    this.snackBar.open(
      '🚀 Fill Gaps started — processing up to 1,000 domains in the background…',
      'Close', { duration: 5000 }
    );

    try {
      // Collect currently displayed domains to prioritize them
      const displayedDomains = this.auctions().map(a => a.domain).filter(d => d);
      console.log('[Fill Gaps] Sending request with payload:', payload, 'prioritized_domains:', displayedDomains.length, 'only_displayed: false');
      const res = await firstValueFrom(this.api.triggerBulkRefresh(payload.filters, false, payload.sort_by, payload.sort_order, displayedDomains, false));
      console.log('[Fill Gaps] Response:', res);

      // API returns immediately with in_progress status and job_id
      if (res.success && res.in_progress && res.job_id) {
        this.fillGapsJobId.set(res.job_id);
        // Start polling for progress
        this.startProgressPolling(res.job_id, 'fill_gaps');
      } else if ((res as any).skipped) {
        this.fillGapsInProgress.set(false);
        this.fillGapsProgress.set(null);
        this.fillGapsStartedAt.set(null);
        this.refreshProgressClockState();
        this.snackBar.open(
          '✅ All scored domains already have fresh metrics — nothing to refresh!',
          'Close', { duration: 6000 }
        );
      } else {
        this.fillGapsInProgress.set(false);
        this.fillGapsProgress.set(null);
        this.fillGapsStartedAt.set(null);
        this.refreshProgressClockState();
        const msg = (res as any).error || 'Failed to trigger refresh';
        this.snackBar.open(`❌ ${msg}`, 'Close', { duration: 6000, panelClass: ['error-snackbar'] });
      }
    } catch (e: any) {
      this.fillGapsInProgress.set(false);
      this.fillGapsProgress.set(null);
      this.fillGapsStartedAt.set(null);
      this.refreshProgressClockState();
      console.error('[Fill Gaps] Error:', e);
      const errorMsg = e.error?.detail || e.error?.error || 'Failed to trigger Fill-the-Gaps refresh';
      this.snackBar.open(`❌ ${errorMsg}`, 'Close', { duration: 6000, panelClass: ['error-snackbar'] });
    }
  }

  async triggerForceRefresh() {
    // Prevent duplicate requests
    if (this.forceRefreshInProgress()) {
      this.snackBar.open('⏳ Force Refresh is already running…', 'Close', { duration: 3000 });
      return;
    }

    // Same filter set as the table, passed to force-refresh endpoint
    const filters: Record<string, any> = {};
    if (this.preferredOnly()) filters['preferred'] = true;
    if (this.scoredOnly()) filters['scored'] = true;
    if (this.statisticsOnly()) filters['has_statistics'] = true;
    if (this.expirationFromDate()) filters['expiration_from_date'] = this.expirationFromDate();
    if (this.expirationToDate()) filters['expiration_to_date'] = this.expirationToDate();
    if (this.selectedPlatforms().length) filters['auction_sites'] = this.selectedPlatforms();
    if (this.selectedTlds().length) filters['tlds'] = this.selectedTlds();
    if (this.offeringType()) filters['offering_type'] = this.offeringType();
    if (this.minScore() !== null) filters['min_score'] = this.minScore();
    if (this.maxScore() !== null) filters['max_score'] = this.maxScore();

    const payload = {
      filters,
      sort_by: this.sortBy(),
      sort_order: this.sortOrder()
    };

    // Set processing state
    this.forceRefreshInProgress.set(true);
    this.forceRefreshStartedAt.set(Date.now());
    this.forceRefreshProgress.set({ percent: 0, message: 'Starting...' });
    this.refreshProgressClockState();

    // Show immediate feedback
    this.snackBar.open(
      '⚡ Force Refresh started — processing up to 1,000 domains in the background…',
      'Close', { duration: 5000 }
    );

    try {
      // Collect currently displayed domains to prioritize them
      const displayedDomains = this.auctions().map(a => a.domain).filter(d => d);
      console.log('[Force Refresh] Sending request with payload:', payload, 'prioritized_domains:', displayedDomains.length, 'only_displayed: false');
      const res = await firstValueFrom(this.api.triggerForceRefresh(payload.filters, payload.sort_by, payload.sort_order, displayedDomains, false));
      console.log('[Force Refresh] Response:', res);

      if (res.success && res.in_progress && res.job_id) {
        this.forceRefreshJobId.set(res.job_id);
        // Start polling for progress
        this.startProgressPolling(res.job_id, 'force_refresh');
      } else {
        this.forceRefreshInProgress.set(false);
        this.forceRefreshProgress.set(null);
        this.forceRefreshStartedAt.set(null);
        this.refreshProgressClockState();
        const msg = (res as any).error || 'Failed to trigger force refresh';
        this.snackBar.open(`❌ ${msg}`, 'Close', { duration: 6000, panelClass: ['error-snackbar'] });
      }
    } catch (e: any) {
      this.forceRefreshInProgress.set(false);
      this.forceRefreshProgress.set(null);
      this.forceRefreshStartedAt.set(null);
      this.refreshProgressClockState();
      console.error('[Force Refresh] Error:', e);
      const errorMsg = e.error?.detail || e.error?.error || 'Failed to trigger force refresh';
      this.snackBar.open(`❌ ${errorMsg}`, 'Close', { duration: 6000, panelClass: ['error-snackbar'] });
    }
  }

  async fetchAuctions() {
    this.loading.set(true);

    // Explicitly unwrap signals to track them as dependencies for the effect
    const sort = this.sortBy();
    const order = this.sortOrder();
    const preferred = this.preferredOnly();
    const scored = this.scoredOnly();
    const hasStatistics = this.statisticsOnly();
    const minS = this.minScore();
    const maxS = this.maxScore();
    const platforms = this.selectedPlatforms();
    const tlds = this.selectedTlds();
    const offType = this.offeringType();
    const normalizedExpirationRange = this.getNormalizedExpirationRange(
      this.expirationFromDate(),
      this.expirationToDate(),
    );
    const expFrom = normalizedExpirationRange.from;
    const expTo = normalizedExpirationRange.to;
    const currentOffset = this.offset();
    const currentLimit = this.limit();

    try {
      const filters = {
        limit: currentLimit,
        offset: currentOffset,
        sort_by: sort,
        order: order,
        preferred: preferred ? true : undefined,
        scored: scored ? true : undefined,
        has_statistics: hasStatistics ? true : undefined,
        expiration_from_date: expFrom || undefined,
        expiration_to_date: expTo || undefined,
        min_score: minS ?? undefined,
        max_score: maxS ?? undefined,
        auction_sites: platforms.length > 0 ? platforms : undefined,
        tlds: tlds.length > 0 ? tlds : undefined,
        offering_type: offType || undefined
      };

      // Update URL silently so users can bookmark or refresh with current filters
      const queryParams: any = {
        sort: sort !== 'expiration_date' ? sort : undefined,
        order: order !== 'asc' ? order : undefined,
        preferred: preferred ? 'true' : undefined,
        scored: scored ? 'true' : undefined,
        has_statistics: hasStatistics ? 'true' : undefined,
        min_score: minS ?? undefined,
        max_score: maxS ?? undefined,
        platforms: platforms.length > 0 ? platforms.join(',') : undefined,
        tlds: tlds.length > 0 ? tlds.join(',') : undefined,
        offering_type: offType || undefined,
        exp_from: expFrom || undefined,
        exp_to: expTo || undefined
      };

      untracked(() => {
        this.router.navigate([], {
          relativeTo: this.route,
          queryParams: queryParams,
          replaceUrl: true
        });
      });

      const res = await firstValueFrom(this.api.getAuctionsReport(filters));

      this.auctions.set(res.auctions);
      this.totalCount.set(res.total_count);
    } catch (e) {
      console.error('Failed to load auctions:', e);
      this.auctions.set([]);
      this.totalCount.set(0);
      this.snackBar.open('Failed to load marketplace results for the current filters.', 'Close', { duration: 4000 });
    } finally {
      this.loading.set(false);
    }
  }

  toggleSort(field: string) {
    if (this.sortBy() === field) {
      this.sortOrder.set(this.sortOrder() === 'asc' ? 'desc' : 'asc');
    } else {
      this.sortBy.set(field);

      const defaultDesc = ['domain_rating', 'organic_traffic', 'keywords_count', 'backlinks', 'score', 'referring_domains'];
      const defaultAsc = ['backlinks_spam_score'];

      if (defaultDesc.includes(field)) {
        this.sortOrder.set('desc');
      } else if (defaultAsc.includes(field)) {
        this.sortOrder.set('asc');
      } else {
        this.sortOrder.set('asc');
      }
    }
    this.offset.set(0); // Reset pagination
  }

  togglePreferred() {
    this.preferredOnly.set(!this.preferredOnly());
    this.offset.set(0);
  }

  toggleScored() {
    this.scoredOnly.set(!this.scoredOnly());
    this.offset.set(0);
  }

  toggleStatistics() {
    this.statisticsOnly.set(!this.statisticsOnly());
    this.offset.set(0);
  }

  // Helper to check if domain is expiring today or soon (within 7 days)
  getExpirationStatus(expirationDate: string): 'today' | 'soon' | 'future' {
    if (!expirationDate) return 'future';
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const expDate = new Date(expirationDate);
    expDate.setHours(0, 0, 0, 0);

    const diffTime = expDate.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays <= 0) return 'today';
    if (diffDays <= 7) return 'soon';
    return 'future';
  }

  toggleFilters() {
    this.showFilters.set(!this.showFilters());
  }

  toggleMobileActions() {
    this.showMobileActions.set(!this.showMobileActions());
  }

  resetFilters() {
    this.preferredOnly.set(false);
    this.scoredOnly.set(false);
    this.statisticsOnly.set(false);
    this.minScore.set(null);
    this.maxScore.set(null);
    this.selectedPlatforms.set([]);
    this.selectedTlds.set([]);
    this.offeringType.set('');
    this.expirationFromDate.set('');
    this.expirationToDate.set('');
    this.offset.set(0);
  }

  togglePlatform(platform: string) {
    const current = this.selectedPlatforms();
    if (current.includes(platform)) {
      this.selectedPlatforms.set(current.filter(p => p !== platform));
    } else {
      this.selectedPlatforms.set([...current, platform]);
    }
    this.offset.set(0);
  }

  toggleTld(tld: string) {
    const current = this.selectedTlds();
    if (current.includes(tld)) {
      this.selectedTlds.set(current.filter(item => item !== tld));
    } else {
      this.selectedTlds.set([...current, tld]);
    }
    this.offset.set(0);
  }

  toggleOtherTlds() {
    const otherTlds = this.otherTlds();
    if (!otherTlds.length) {
      return;
    }

    if (this.allOtherTldsSelected()) {
      this.selectedTlds.set(this.selectedTlds().filter(tld => !otherTlds.includes(tld)));
    } else {
      this.selectedTlds.set(Array.from(new Set([...this.selectedTlds(), ...otherTlds])));
    }
    this.offset.set(0);
  }

  getSortIcon(field: string) {
    if (this.sortBy() !== field) return ArrowUpDown;
    return this.sortOrder() === 'asc' ? ArrowUp : ArrowDown;
  }

  getPlatformClass(site: string) {
    const s = site?.toLowerCase() || '';
    if (s.includes('godaddy')) return 'platform-godaddy';
    if (s.includes('dynadot')) return 'platform-dynadot';
    if (s.includes('namecheap')) return 'platform-namecheap';
    if (s.includes('sedo')) return 'platform-sedo';
    if (s.includes('namesilo')) return 'platform-namesilo';
    return 'platform-default';
  }

  /** Returns a Tailwind color class for the Domain Rating traffic-light indicator */
  getDrClass(dr: number | undefined | null): string {
    const val = dr ?? 0;
    if (val >= 50) return 'text-emerald-500';   // Strong — green
    if (val >= 5) return 'text-amber-500';      // Mid — amber
    return 'text-red-400 opacity-70';            // Weak/zero — red
  }

  /** Returns a color class for the current bid price */
  getBidClass(bid: number | undefined | null): string {
    const val = bid ?? 0;
    if (val <= 20) return 'text-emerald-500';  // Deal price — green
    if (val <= 100) return '';                  // Market rate — neutral
    return 'text-amber-500';                    // Premium bid — amber
  }

  /** Returns a color class for the AI Score */
  getScoreClass(score: number | undefined | null): string {
    if (!score) return 'opacity-20';             // No score yet — very faint
    if (score > 25) return 'text-emerald-500';  // High — green
    if (score >= 3) return 'text-amber-500';    // Mid (3–25) — amber
    return 'text-red-400';                       // Low (<3) — red
  }

  /** Formats an SEO metric number as a shorter string, returns '-' if no stats available */
  fmtMetric(val: number | undefined | null, hasStats: boolean): string {
    if (!hasStats) return '–';
    const n = val ?? 0;
    if (n === 0) return '0';
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(1) + 'k';
    return n.toLocaleString();
  }

  /** Normal format without checking stats */
  fmtNum(val: number | undefined | null): string {
    const n = val ?? 0;
    if (n === 0) return '0';
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(1) + 'k';
    return n.toLocaleString();
  }

  async toggleFavorite(event: Event, item: Auction) {
    event.stopPropagation();
    const newStatus = !item.preferred;

    // Optimistic update
    const current = this.auctions();
    this.auctions.set(current.map(a => a.id === item.id ? { ...a, preferred: newStatus } : a));

    try {
      const res = await firstValueFrom(this.api.togglePreferredAuction(item.id, newStatus));
      if (!res.success) {
        // Rollback
        this.auctions.set(current);
        this.snackBar.open('Failed to update favorite status', 'Close', { duration: 3000 });
      }
    } catch (e) {
      this.auctions.set(current);
      this.snackBar.open('Error updating favorite status', 'Close', { duration: 3000 });
    }
  }

  nextPage() {
    if (this.offset() + this.limit() < this.totalCount()) {
      this.offset.set(this.offset() + this.limit());
    }
  }

  prevPage() {
    this.offset.set(Math.max(0, this.offset() - this.limit()));
  }

  onLimitChange(newLimit: number) {
    this.limit.set(newLimit);
    this.offset.set(0);
  }
}
