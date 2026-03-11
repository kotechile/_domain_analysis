import { Component, inject, signal, computed, effect, OnInit, untracked } from '@angular/core';
import { CommonModule, TitleCasePipe, DatePipe, DecimalPipe } from '@angular/common';
import { RouterLink, ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api';
import { LucideAngularModule, Search, Filter, ArrowUpDown, ArrowUp, ArrowDown, ExternalLink, Sparkles, TrendingUp, History, ShieldCheck, Star, Target, Zap } from 'lucide-angular';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { CreditService } from '../../services/credit';
import { firstValueFrom } from 'rxjs';
import { Auction } from '../../models/domain.model';

@Component({
  selector: 'app-marketplace',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LucideAngularModule, TitleCasePipe, DatePipe, DecimalPipe, MatSnackBarModule],
  templateUrl: './marketplace.html',
  styles: [`
    .table-container {
      @apply overflow-x-auto rounded-2xl border border-opacity-10;
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
    
    .search-input {
      @apply w-full h-11 pl-10 pr-4 rounded-xl text-sm font-semibold border-none transition-all shadow-sm;
      background: var(--card-bg);
      color: var(--text-color);
      box-shadow: 0 0 0 1px var(--border-color);
    }
    .search-input:focus {
      @apply ring-2 ring-offset-0;
      box-shadow: 0 0 0 2px var(--accent-color);
    }
  `]
})
export class MarketplaceComponent implements OnInit {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  // Icons
  readonly Search = Search;
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
  readonly Zap = Zap;

  // State Signals
  auctions = signal<Auction[]>([]);
  loading = signal<boolean>(true);
  totalCount = signal<number>(0);

  // Filter Signals
  searchQuery = signal<string>('');
  sortBy = signal<string>('expiration_date');
  sortOrder = signal<'asc' | 'desc'>('asc');
  preferredOnly = signal<boolean>(false);
  scoredOnly = signal<boolean>(false);

  // Advanced Filters
  minScore = signal<number | null>(null);
  maxScore = signal<number | null>(null);
  selectedPlatforms = signal<string[]>([]);
  offeringType = signal<string>(''); // 'auction', 'buy_now', 'backorder'
  showFilters = signal<boolean>(false);

  // Date Filters (Empty by default to show all results)
  expirationFromDate = signal<string>('');
  expirationToDate = signal<string>('');

  limit = signal<number>(50);
  offset = signal<number>(0);

  activeFilterCount = computed(() => {
    let count = 0;
    if (this.searchQuery()) count++;
    if (this.preferredOnly()) count++;
    if (this.minScore() !== null && this.minScore() !== undefined) count++;
    if (this.maxScore() !== null && this.maxScore() !== undefined) count++;
    if (this.selectedPlatforms().length > 0) count++;
    if (this.offeringType()) count++;
    if (this.expirationFromDate() || this.expirationToDate()) count++;
    return count;
  });

  private snackBar = inject(MatSnackBar);
  private creditService = inject(CreditService);

  constructor() {
    // Automatically re-fetch whenever a filter signal changes
    effect(() => {
      this.fetchAuctions();
    });
  }

  ngOnInit() {
    // Sync signals from URL query parameters on initial load so filters persist across refreshes
    const qp = this.route.snapshot.queryParams;

    if (qp['search']) this.searchQuery.set(qp['search']);
    if (qp['sort']) this.sortBy.set(qp['sort']);
    if (qp['order']) this.sortOrder.set(qp['order'] as 'asc' | 'desc');
    if (qp['preferred']) this.preferredOnly.set(qp['preferred'] === 'true');
    if (qp['scored']) this.scoredOnly.set(qp['scored'] === 'true');
    if (qp['min_score']) this.minScore.set(Number(qp['min_score']));
    if (qp['max_score']) this.maxScore.set(Number(qp['max_score']));
    if (qp['platforms']) this.selectedPlatforms.set(qp['platforms'].split(','));
    if (qp['offering_type']) this.offeringType.set(qp['offering_type']);
    if (qp['exp_from']) this.expirationFromDate.set(qp['exp_from']);
    if (qp['exp_to']) this.expirationToDate.set(qp['exp_to']);
  }

  isStale(dateStr: string | undefined): boolean {
    if (!dateStr) return true;
    const lastUpdate = new Date(dateStr);
    const now = new Date();
    const diffHours = (now.getTime() - lastUpdate.getTime()) / (1000 * 60 * 60);
    return diffHours > 24;
  }

  async refreshDomain(event: Event, domain: string) {
    event.stopPropagation();

    if (!confirm(`Refresh SEO metrics for ${domain}? (Cost: 5 credits)`)) {
      return;
    }

    try {
      const res = await firstValueFrom(this.api.triggerDomainRefresh(domain));
      if (res.success) {
        this.snackBar.open(`Refresh triggered for ${domain}. Metrics will update shortly.`, 'Close', { duration: 5000 });
        // Refresh balance in header
        this.creditService.refreshData();
        // Optionally refresh table list, but metrics update via n8n so it might take a moment
        this.fetchAuctions();
      }
    } catch (e: any) {
      const errorMsg = e.error?.error || 'Failed to trigger refresh';
      this.snackBar.open(errorMsg, 'Close', { duration: 5000, panelClass: ['error-snackbar'] });
    }
  }

  async triggerBulkRefresh() {
    // Build the exact same filter set that the table currently uses
    const filters: Record<string, any> = {};

    if (this.preferredOnly()) filters['preferred'] = true;
    if (this.scoredOnly()) filters['scored'] = true;
    if (this.expirationFromDate()) filters['expiration_from_date'] = this.expirationFromDate();
    if (this.expirationToDate()) filters['expiration_to_date'] = this.expirationToDate();
    if (this.selectedPlatforms().length) filters['auction_sites'] = this.selectedPlatforms();
    if (this.offeringType()) filters['offering_type'] = this.offeringType();
    if (this.minScore() !== null) filters['min_score'] = this.minScore();
    if (this.maxScore() !== null) filters['max_score'] = this.maxScore();

    // Snackbar loading indicator
    const loadingSnack = this.snackBar.open(
      '🔍 Scanning for domains with missing metrics…', '', { duration: 0 }
    );

    try {
      const res = await firstValueFrom(this.api.triggerBulkRefresh(filters, false));
      loadingSnack.dismiss();

      if (res.success) {
        if ((res as any).skipped) {
          this.snackBar.open(
            '✅ All scored domains already have fresh metrics — nothing to refresh!',
            'Close', { duration: 6000 }
          );
        } else {
          this.snackBar.open(
            `🚀 Filling gaps for ${res.triggered_count?.toLocaleString() ?? '?'} domains · ${res.cost} credits deducted · Results in ~2 min`,
            'Close', { duration: 8000 }
          );
          this.creditService.refreshData();
        }
      } else {
        const msg = (res as any).error || 'Failed to trigger refresh';
        this.snackBar.open(`❌ ${msg}`, 'Close', { duration: 6000, panelClass: ['error-snackbar'] });
      }
    } catch (e: any) {
      loadingSnack.dismiss();
      const errorMsg = e.error?.detail || e.error?.error || 'Failed to trigger Fill-the-Gaps refresh';
      this.snackBar.open(`❌ ${errorMsg}`, 'Close', { duration: 6000, panelClass: ['error-snackbar'] });
    }
  }

  async triggerForceRefresh() {
    // Same filter set as the table, passed to force-refresh endpoint
    const filters: Record<string, any> = {};
    if (this.preferredOnly()) filters['preferred'] = true;
    if (this.scoredOnly()) filters['scored'] = true;
    if (this.expirationFromDate()) filters['expiration_from_date'] = this.expirationFromDate();
    if (this.expirationToDate()) filters['expiration_to_date'] = this.expirationToDate();
    if (this.selectedPlatforms().length) filters['auction_sites'] = this.selectedPlatforms();
    if (this.offeringType()) filters['offering_type'] = this.offeringType();
    if (this.minScore() !== null) filters['min_score'] = this.minScore();
    if (this.maxScore() !== null) filters['max_score'] = this.maxScore();

    const loadingSnack = this.snackBar.open(
      '⚡ Preparing force refresh…', '', { duration: 0 }
    );

    try {
      const res = await firstValueFrom(this.api.triggerForceRefresh(filters));
      loadingSnack.dismiss();

      if (res.success) {
        this.snackBar.open(
          `⚡ Force refreshing ${res.triggered_count?.toLocaleString() ?? '?'} domains · ${res.cost} credits deducted · Results in ~2 min`,
          'Close', { duration: 8000 }
        );
        this.creditService.refreshData();
      } else {
        const msg = (res as any).error || 'Failed to trigger force refresh';
        this.snackBar.open(`❌ ${msg}`, 'Close', { duration: 6000, panelClass: ['error-snackbar'] });
      }
    } catch (e: any) {
      loadingSnack.dismiss();
      const errorMsg = e.error?.detail || e.error?.error || 'Failed to trigger force refresh';
      this.snackBar.open(`❌ ${errorMsg}`, 'Close', { duration: 6000, panelClass: ['error-snackbar'] });
    }
  }

  async fetchAuctions() {
    this.loading.set(true);

    // Explicitly unwrap signals to track them as dependencies for the effect
    const search = this.searchQuery();
    const sort = this.sortBy();
    const order = this.sortOrder();
    const preferred = this.preferredOnly();
    const scored = this.scoredOnly();
    const minS = this.minScore();
    const maxS = this.maxScore();
    const platforms = this.selectedPlatforms();
    const offType = this.offeringType();
    const expFrom = this.expirationFromDate();
    const expTo = this.expirationToDate();
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
        expiration_from_date: expFrom || undefined,
        expiration_to_date: expTo || undefined,
        search: search || undefined,
        min_score: minS ?? undefined,
        max_score: maxS ?? undefined,
        auction_sites: platforms.length > 0 ? platforms : undefined,
        offering_type: offType || undefined
      };

      // Update URL silently so users can bookmark or refresh with current filters
      const queryParams: any = {
        search: search || undefined,
        sort: sort !== 'expiration_date' ? sort : undefined,
        order: order !== 'asc' ? order : undefined,
        preferred: preferred ? 'true' : undefined,
        scored: scored ? 'true' : undefined,
        min_score: minS ?? undefined,
        max_score: maxS ?? undefined,
        platforms: platforms.length > 0 ? platforms.join(',') : undefined,
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
    } finally {
      this.loading.set(false);
    }
  }

  toggleSort(field: string) {
    if (this.sortBy() === field) {
      this.sortOrder.set(this.sortOrder() === 'asc' ? 'desc' : 'asc');
    } else {
      this.sortBy.set(field);
      this.sortOrder.set('asc');
    }
    this.offset.set(0); // Reset pagination
  }

  onSearch(event: any) {
    this.searchQuery.set(event.target.value);
    this.offset.set(0);
  }

  togglePreferred() {
    this.preferredOnly.set(!this.preferredOnly());
    this.offset.set(0);
  }

  toggleFilters() {
    this.showFilters.set(!this.showFilters());
  }

  resetFilters() {
    this.searchQuery.set('');
    this.preferredOnly.set(false);
    this.scoredOnly.set(false);
    this.minScore.set(null);
    this.maxScore.set(null);
    this.selectedPlatforms.set([]);
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

  /** Formats a number as a shorter string, returns em dash for zero */
  fmtNum(val: number | undefined | null): string {
    const n = val ?? 0;
    if (n === 0) return '–';
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
}
