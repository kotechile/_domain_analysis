import { Component, inject, signal, effect, OnInit } from '@angular/core';
import { CommonModule, DecimalPipe, DatePipe } from '@angular/common';
import { CreditService } from '../../services/credit';
import { ActivatedRoute } from '@angular/router';
import { LucideAngularModule, CreditCard, History, Zap, ShieldCheck, ArrowUpRight, ArrowDownRight, RefreshCw, AlertCircle, Crown, Sparkles } from 'lucide-angular';

@Component({
  selector: 'app-billing',
  standalone: true,
  imports: [CommonModule, LucideAngularModule, DecimalPipe, DatePipe],
  templateUrl: './billing.html',
  styles: [`
    .billing-card {
      @apply rounded-3xl border border-opacity-10 backdrop-blur-md p-8 transition-all;
      background: var(--card-bg);
      border-color: var(--border-color);
    }

    .tier-badge {
      @apply px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest;
      background: rgba(var(--accent-color-rgb), 0.1);
      color: var(--accent-color);
    }

    .plan-card {
      @apply rounded-3xl border-2 p-6 transition-all cursor-pointer relative overflow-hidden;
      background: var(--card-bg);
    }

    .plan-card:hover {
      @apply scale-[1.02] shadow-xl;
    }

    .plan-card.active-plan {
      border-color: var(--accent-color);
      box-shadow: 0 0 0 1px var(--accent-color), 0 4px 24px -4px rgba(var(--accent-color-rgb), 0.3);
    }

    .plan-card.popular {
      border-color: rgba(var(--accent-color-rgb), 0.4);
    }
  `]
})
export class BillingComponent implements OnInit {
  creditService = inject(CreditService);
  private route = inject(ActivatedRoute);

  readonly CreditCard = CreditCard;
  readonly History = History;
  readonly Zap = Zap;
  readonly ShieldCheck = ShieldCheck;
  readonly ArrowUpRight = ArrowUpRight;
  readonly ArrowDownRight = ArrowDownRight;
  readonly RefreshCw = RefreshCw;
  readonly AlertCircle = AlertCircle;
  readonly Crown = Crown;
  readonly Sparkles = Sparkles;

  buying = signal<string | null>(null);
  checkoutSuccess = signal(false);
  checkoutCancelled = signal(false);
  stripeConfigured = signal(false);
  activeTab = signal<'packs' | 'subscriptions' | 'history'>('packs');

  staticPurchaseOptions = [
    { amount: 50, price: 5, label: 'Starter Pack', icon: Zap, priceIdKey: 'credit_pack_small' },
    { amount: 250, price: 20, label: 'Pro Bundle', icon: ShieldCheck, popular: true, priceIdKey: 'credit_pack_medium' },
    { amount: 1000, price: 75, label: 'Enterprise Scout', icon: History, priceIdKey: 'credit_pack_large' },
  ];

  staticSubscriptions = [
    { id: 'pro', name: 'Pro', price: 19, credits: 200, icon: Zap, priceIdKey: 'pro' },
    { id: 'agency', name: 'Agency', price: 49, credits: 9999, icon: Crown, priceIdKey: 'agency' },
  ];

  constructor() {
    effect(() => {
      const plans = this.creditService.plans();
      if (plans && plans.publishable_key) {
        this.stripeConfigured.set(true);
      }
    });
  }

  ngOnInit() {
    this.creditService.loadPlans();

    this.route.queryParams.subscribe(params => {
      if (params['checkout'] === 'success') {
        this.checkoutSuccess.set(true);
        this.creditService.refreshData();
        setTimeout(() => this.checkoutSuccess.set(false), 8000);
      } else if (params['checkout'] === 'cancelled') {
        this.checkoutCancelled.set(true);
        setTimeout(() => this.checkoutCancelled.set(false), 5000);
      }
    });
  }

  getPriceId(priceIdKey: string): string | null {
    const plans = this.creditService.plans();
    if (!plans) return null;

    const pack = plans.credit_packs.find(p => p.id === priceIdKey);
    if (pack) return pack.price_id;

    const sub = plans.subscriptions.find(s => s.id === priceIdKey);
    if (sub) return sub.price_id;

    return null;
  }

  async recharge(priceIdKey: string, amount: number) {
    if (this.buying()) return;

    const priceId = this.getPriceId(priceIdKey);
    if (!priceId) {
      alert('This plan is not yet configured. Please contact support or try again later.');
      return;
    }

    this.buying.set(priceIdKey);
    try {
      await this.creditService.checkout(priceId, 'payment', 1);
    } finally {
      this.buying.set(null);
    }
  }

  async subscribe(priceIdKey: string) {
    if (this.buying()) return;

    const priceId = this.getPriceId(priceIdKey);
    if (!priceId) {
      alert('This subscription is not yet configured. Please contact support.');
      return;
    }

    this.buying.set(priceIdKey);
    try {
      await this.creditService.checkout(priceId, 'subscription', 1);
    } finally {
      this.buying.set(null);
    }
  }

  refresh() {
    this.creditService.refreshData();
  }
}