import { Injectable, inject, signal, effect, computed } from '@angular/core';
import { ApiService } from './api';
import { SupabaseService } from './supabase';
import { firstValueFrom } from 'rxjs';
import { BalanceResponse, TransactionResponse } from '../models/domain.model';

@Injectable({
  providedIn: 'root'
})
export class CreditService {
  private api = inject(ApiService);
  private auth = inject(SupabaseService);

  // States
  balance = signal<number>(0);
  transactions = signal<TransactionResponse[]>([]);
  loading = signal<boolean>(false);
  error = signal<string | null>(null);

  // Computed Values
  isLowBalance = computed(() => this.balance() < 10);
  formattedBalance = computed(() => `$${this.balance().toFixed(2)}`);

  constructor() {
    // 1. Initial Load
    // Try refreshing data regardless of auth state for development fallback
    this.refreshData();

    effect(() => {
      const user = this.auth.user();
      if (user) {
        this.refreshData();
      }
    });

    // 2. Local-only mock updates for immediate feedback (deduction prediction)
    // In a real SaaS, we would also use Supabase Realtime here.
  }

  async refreshData() {
    this.loading.set(true);
    try {
      const [balanceRes, transactionsRes] = await Promise.all([
        firstValueFrom(this.api.getBalance()),
        firstValueFrom(this.api.getTransactions())
      ]);

      this.balance.set(balanceRes.balance);
      this.transactions.set(transactionsRes);
      this.error.set(null);
    } catch (e: any) {
      console.error('Failed to refresh credit data:', e);
      this.error.set('Could not fetch credit balance.');
    } finally {
      this.loading.set(false);
    }
  }

  /**
   * Mock a deduction for immediate UI feedback. 
   * Useful when starting a long-running analysis.
   */
  async predictDeduction(amount: number) {
    this.balance.update(current => Math.max(0, current - amount));
  }

  async mockPurchase(amount: number) {
    try {
      const res = await firstValueFrom(this.api.purchaseCredits(amount, 'Top-up through Dashboard'));
      if (res.success) {
        this.balance.set(res.new_balance);
        await this.refreshData(); // Sync full state
        return true;
      }
      return false;
    } catch (e: any) {
      this.error.set('Failed to purchase credits.');
      return false;
    }
  }
}
