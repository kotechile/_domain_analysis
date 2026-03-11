import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { LucideAngularModule, Search, Table, Settings, CreditCard, ChevronRight, LayoutDashboard, BrainCircuit, History } from 'lucide-angular';
import { SupabaseService } from '../../services/supabase';
import { CreditService } from '../../services/credit';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive, LucideAngularModule],
  templateUrl: './sidebar.html',
  styles: [`
    :host {
      @apply fixed left-0 top-0 h-full w-64 border-r border-opacity-10 dark:border-white/5 transition-all duration-500 z-50;
      background: var(--card-bg);
      border-color: var(--border-color);
    }
    
    .nav-item {
      @apply flex items-center space-x-3 px-4 py-3.5 rounded-2xl text-sm font-bold opacity-60 transition-all active:scale-95 mx-3;
      color: var(--text-color);
    }
    
    .nav-item:hover {
      @apply opacity-100;
      background: rgba(var(--accent-color-rgb, 13 110 253) / 0.05);
    }
    
    .nav-item.active {
      @apply opacity-100;
      background: rgba(var(--accent-color-rgb, 13 110 253) / 0.1);
      color: var(--accent-color);
    }
    
    .logo-section {
      @apply p-8 mb-4;
    }
    
    .sidebar-footer {
      @apply absolute bottom-0 left-0 w-full p-6 border-t border-opacity-5;
      border-color: var(--border-color);
    }
  `]
})
export class SidebarComponent {
  supabase = inject(SupabaseService);
  creditService = inject(CreditService);

  readonly Search = Search;
  readonly Table = Table;
  readonly Settings = Settings;
  readonly CreditCard = CreditCard;
  readonly ChevronRight = ChevronRight;
  readonly LayoutDashboard = LayoutDashboard;
  readonly BrainCircuit = BrainCircuit;
  readonly History = History;

  navItems = [
    { path: '/', label: 'Deep Analysis', icon: BrainCircuit },
    { path: '/marketplace', label: 'Marketplace', icon: Table },
    { path: '/billing', label: 'Billing & Credits', icon: CreditCard },
    { path: '/themes', label: 'Settings & UI', icon: Settings }
  ];
}
