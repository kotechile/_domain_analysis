import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ApiService } from '../../services/api';
import { CreditService } from '../../services/credit';
import { LucideAngularModule, Search, Zap, ShieldCheck, History, TrendingUp, Sparkles, AlertCircle } from 'lucide-angular';
import { firstValueFrom } from 'rxjs';

@Component({
  selector: 'app-domain-analysis',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LucideAngularModule, RouterLink],
  templateUrl: './domain-analysis.html',
  styles: [`
    .hero-glow {
      @apply absolute -top-24 left-1/2 -translate-x-1/2 w-[600px] h-[300px] blur-[120px] opacity-20 pointer-events-none;
      background: radial-gradient(circle, var(--accent-color) 0%, transparent 70%);
    }
    
    .search-group:focus-within {
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent-color), transparent 70%);
    }

    .badge-premium {
      @apply px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border border-opacity-20;
      border-color: var(--accent-color);
      color: var(--accent-color);
    }
  `]
})
export class DomainAnalysisComponent {
  private fb = inject(FormBuilder);
  private api = inject(ApiService);
  private router = inject(Router);
  creditService = inject(CreditService);

  // Icons
  readonly Search = Search;
  readonly Zap = Zap;
  readonly ShieldCheck = ShieldCheck;
  readonly History = History;
  readonly TrendingUp = TrendingUp;
  readonly Sparkles = Sparkles;
  readonly AlertCircle = AlertCircle;

  // Signals
  isLoading = signal(false);
  error = signal<string | null>(null);

  // Forms
  analysisForm = this.fb.group({
    domain: ['', [Validators.required, Validators.pattern(/^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$/)]],
    mode: ['dual']
  });

  async startAnalysis() {
    if (this.analysisForm.invalid || this.isLoading()) return;

    const domain = this.api.formatDomain(this.analysisForm.value.domain || '');
    const mode = this.analysisForm.value.mode || 'dual';

    this.isLoading.set(true);
    this.error.set(null);

    // Optimistic UI: Predict the credit deduction (e.g., 0.50 credits for Dual)
    const predictedCost = mode === 'dual' ? 0.50 : 0.15;
    this.creditService.predictDeduction(predictedCost);

    try {
      const res = await firstValueFrom(this.api.analyzeDomain(domain, mode));
      if (res.success) {
        this.router.navigate(['/reports', domain]);
      } else {
        this.error.set(res.message);
        await this.creditService.refreshData(); // Re-sync actual balance on failure
      }
    } catch (e: any) {
      this.error.set(e.error?.detail || 'Analysis failed. Please check your internet connection or account balance.');
      await this.creditService.refreshData();
    } finally {
      this.isLoading.set(false);
    }
  }

  setMode(mode: 'dual' | 'legacy') {
    this.analysisForm.patchValue({ mode });
  }
}
