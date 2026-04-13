import { Component, inject, signal } from '@angular/core';
import { CommonModule, DecimalPipe, DatePipe } from '@angular/common';
import { CreditService } from '../../services/credit';
import { LucideAngularModule, CreditCard, History, Zap, ShieldCheck, ArrowUpRight, ArrowDownRight, RefreshCw, AlertCircle } from 'lucide-angular';

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
  `]
})
export class BillingComponent {
  creditService = inject(CreditService);

  readonly CreditCard = CreditCard;
  readonly History = History;
  readonly Zap = Zap;
  readonly ShieldCheck = ShieldCheck;
  readonly ArrowUpRight = ArrowUpRight;
  readonly ArrowDownRight = ArrowDownRight;
  readonly RefreshCw = RefreshCw;
  readonly AlertCircle = AlertCircle;

  purchaseOptions = [
    { amount: 50, price: 5, label: 'Starter Pack', icon: Zap },
    { amount: 250, price: 20, label: 'Pro Bundle', icon: ShieldCheck, popular: true },
    { amount: 1000, price: 75, label: 'Enterprise Scout', icon: History }
  ];

  buying = signal<boolean>(false);

  async recharge(amount: number) {
    if (this.buying()) return;
    
    // Warn the user that the payment gateway is pending
    alert("Stripe Checkout Integration is pending. Direct purchases are currently disabled for security. Please contact support to manually top up your account.");
    return;
  }

  refresh() {
    this.creditService.refreshData();
  }
}
