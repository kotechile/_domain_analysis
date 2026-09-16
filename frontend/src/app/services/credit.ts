import { Injectable, inject, signal, effect, computed } from '@angular/core';
import { ApiService } from './api';
import { SupabaseService } from './supabase';
import { firstValueFrom } from 'rxjs';
import { BalanceResponse, TransactionResponse, PlansResponse, CreditPack, SubscriptionPlan } from '../models/domain.model';

@Injectable({
  providedIn: 'root'
})
export class CreditService {
  private api = inject(ApiService);
  private auth = inject(SupabaseService);

  balance = signal<number>(0);
  transactions = signal<TransactionResponse[]>([]);
  loading = signal<boolean>(false);
  error = signal<string | null>(null);
  plans = signal<PlansResponse | null>(null);
  plansLoading = signal<boolean>(false);

  isLowBalance = computed(() => this.balance() < 10);
  formattedBalance = computed(() => `$${this.balance().toFixed(2)}`);

  constructor() {
    this.refreshData();

    effect(() => {
      const user = this.auth.user();
      if (user) {
        this.refreshData();
      }
    });
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

  async loadPlans() {
    this.plansLoading.set(true);
    try {
      const plansRes = await firstValueFrom(this.api.getPlans());
      this.plans.set(plansRes);
    } catch (e: any) {
      console.error('Failed to load plans:', e);
    } finally {
      this.plansLoading.set(false);
    }
  }

  async checkout(priceId: string, mode: string = 'payment', quantity: number = 1): Promise<string | null> {
    const baseUrl = window.location.origin;
    const successUrl = `${baseUrl}/app/billing?checkout=success&session_id={CHECKOUT_SESSION_ID}`;
    const cancelUrl = `${baseUrl}/app/billing?checkout=cancelled`;

    try {
      const res = await firstValueFrom(
        this.api.createCheckoutSession(priceId, mode, quantity, successUrl, cancelUrl)
      );

      if (res.url) {
        window.location.href = res.url;
        return res.session_id;
      }

      if (res.session_id) {
        return res.session_id;
      }

      this.error.set('Failed to start checkout. Stripe may not be configured.');
      return null;
    } catch (e: any) {
      console.error('Checkout failed:', e);
      this.error.set(e?.error?.detail || 'Checkout failed. Please try again.');
      return null;
    }
  }

  async predictDeduction(amount: number) {
    this.balance.update(current => Math.max(0, current - amount));
  }

  async mockPurchase(amount: number) {
    try {
      const res = await firstValueFrom(this.api.purchaseCredits(amount, 'Top-up through Dashboard'));
      if (res.success) {
        this.balance.set(res.new_balance);
        await this.refreshData();
        return true;
      }
      return false;
    } catch (e: any) {
      this.error.set('Failed to purchase credits.');
      return false;
    }
  }
}