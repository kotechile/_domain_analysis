import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ThemeService, ThemeMode } from '../../services/theme';
import { SupabaseService } from '../../services/supabase';
import { CreditService } from '../../services/credit';
import { LucideAngularModule, Moon, Sun, Monitor, Palette, Search, Bell, User } from 'lucide-angular';
import { RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, LucideAngularModule, RouterLink, RouterLinkActive],
  templateUrl: './header.html',
  styles: [`
    :host {
      @apply block z-40 transition-all duration-500;
    }
    
    .active-theme i-lucide {
      @apply opacity-100;
      color: var(--accent-color);
    }
  `]
})
export class HeaderComponent {
  themeService = inject(ThemeService);
  supabase = inject(SupabaseService);
  creditService = inject(CreditService);

  readonly Sun = Sun;
  readonly Moon = Moon;
  readonly Palette = Palette;
  readonly Search = Search;
  readonly Bell = Bell;
  readonly User = User;

  themes: { mode: ThemeMode; label: string; icon: any }[] = [
    { mode: 'light-modern', label: 'Modern Light', icon: Sun },
    { mode: 'light-plus', label: 'Light+', icon: Palette },
    { mode: 'dark-modern', label: 'Modern Dark', icon: Moon },
    { mode: 'dark-plus', label: 'Dark+', icon: Palette }
  ];

  changeTheme(mode: ThemeMode) {
    this.themeService.setTheme(mode);
  }
}
