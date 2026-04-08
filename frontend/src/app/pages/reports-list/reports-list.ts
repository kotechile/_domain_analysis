import { Component, inject, signal, OnInit, effect, computed } from '@angular/core';
import { CommonModule, DatePipe, TitleCasePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../services/api';
import { LucideAngularModule, Search, History, Filter, ArrowRight, ExternalLink, Trash2, BrainCircuit, Zap, CheckCircle, Clock, RotateCcw } from 'lucide-angular';
import { firstValueFrom } from 'rxjs';
import { DomainAnalysisReport } from '../../models/domain.model';

@Component({
  selector: 'app-reports-list',
  standalone: true,
  imports: [CommonModule, RouterLink, LucideAngularModule, DatePipe, TitleCasePipe],
  templateUrl: './reports-list.html',
  styles: [`
    .table-container {
      @apply rounded-3xl border border-opacity-10 backdrop-blur-md overflow-hidden;
      border-color: var(--border-color);
      background: var(--card-bg);
    }
    th {
      @apply px-6 py-5 text-left text-xs font-black uppercase tracking-[0.2em] opacity-40;
      color: var(--text-color);
    }
    td {
      @apply px-6 py-5 text-sm font-medium border-t border-opacity-5 transition-colors;
      border-color: var(--border-color);
      color: var(--text-color);
    }
    tr:hover td {
      background: rgba(var(--accent-color-rgb), 0.05);
    }
    .status-badge {
      @apply px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest flex items-center space-x-1.5 w-fit;
    }
    .status-completed { background: #10b98120; color: #10b981; }
    .status-progress { background: #3b82f620; color: #3b82f6; }
    .status-failed { background: #ef444420; color: #ef4444; }
    .status-pending { background: #94a3b820; color: #94a3b8; }
  `]
})
export class ReportsListComponent implements OnInit {
  private api = inject(ApiService);

  // Icons
  readonly Search = Search;
  readonly History = History;
  readonly Filter = Filter;
  readonly ArrowRight = ArrowRight;
  readonly ExternalLink = ExternalLink;
  readonly Trash2 = Trash2;
  readonly BrainCircuit = BrainCircuit;
  readonly Zap = Zap;
  readonly CheckCircle = CheckCircle;
  readonly Clock = Clock;
  readonly RotateCcw = RotateCcw;

  // State
  reports = signal<DomainAnalysisReport[]>([]);
  loading = signal(true);
  error = signal<string | null>(null);
  selectedDomains = signal<Set<string>>(new Set());
  
  // Computed
  isAllSelected = computed(() => {
    const currentReports = this.reports();
    const selected = this.selectedDomains();
    return currentReports.length > 0 && currentReports.every(r => selected.has(r.domain_name));
  });
  
  // Pagination
  limit = signal(15);
  offset = signal(0);
  
  ngOnInit() {
    this.fetchReports();
  }

  async fetchReports() {
    this.loading.set(true);
    this.error.set(null);
    try {
      const data = await firstValueFrom(this.api.listReports(this.limit(), this.offset()));
      this.reports.set(data);
    } catch (err) {
      console.error('Failed to load reports:', err);
      this.error.set('Could not load analysis history.');
    } finally {
      this.loading.set(false);
    }
  }

  getModeIcon(report: DomainAnalysisReport) {
    // Determine if it was Deep or Quick based on fields (or mode if we had it)
    return report.llm_analysis ? this.BrainCircuit : this.Zap;
  }

  getStatusClass(status: string) {
    switch (status) {
      case 'completed': return 'status-completed';
      case 'in_progress': return 'status-progress';
      case 'failed': return 'status-failed';
      default: return 'status-pending';
    }
  }

  async deleteReport(domain: string, event: MouseEvent) {
    event.preventDefault();
    event.stopPropagation();
    
    if (confirm(`Are you sure you want to delete the report for ${domain}?`)) {
      try {
        await firstValueFrom(this.api.deleteReport(domain));
        // Remove from selection if present
        this.selectedDomains.update(set => {
          const newSet = new Set(set);
          newSet.delete(domain);
          return newSet;
        });
        // Refresh the list
        await this.fetchReports();
      } catch (err) {
        console.error('Failed to delete report:', err);
        // Error handling is already scoped to the catch block
      }
    }
  }

  toggleSelection(domain: string, event: Event) {
    event.stopPropagation(); // prevent row click
    const checkbox = event.target as HTMLInputElement;
    this.selectedDomains.update(set => {
      const newSet = new Set(set);
      if (checkbox.checked) newSet.add(domain);
      else newSet.delete(domain);
      return newSet;
    });
  }

  toggleAll(event: Event) {
    const checkbox = event.target as HTMLInputElement;
    this.selectedDomains.update(set => {
      const newSet = new Set(set);
      this.reports().forEach(r => {
        if (checkbox.checked) newSet.add(r.domain_name);
        else newSet.delete(r.domain_name);
      });
      return newSet;
    });
  }

  async bulkDelete() {
    const domainsToDelete = Array.from(this.selectedDomains());
    if (domainsToDelete.length === 0) return;
    
    if (confirm(`Are you sure you want to delete ${domainsToDelete.length} selected reports?`)) {
      try {
        await Promise.all(domainsToDelete.map(domain => firstValueFrom(this.api.deleteReport(domain))));
        this.selectedDomains.set(new Set()); // Clear selection
        await this.fetchReports(); // Refresh list
      } catch (err) {
        console.error('Failed to bulk delete reports:', err);
        this.error.set('Failed to delete some or all selected reports.');
      }
    }
  }

  async nextPage() {
    this.offset.set(this.offset() + this.limit());
    await this.fetchReports();
  }

  async prevPage() {
    if (this.offset() > 0) {
      this.offset.set(Math.max(0, this.offset() - this.limit()));
      await this.fetchReports();
    }
  }
}
