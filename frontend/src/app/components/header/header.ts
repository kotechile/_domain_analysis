import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ThemeService, ThemeMode } from '../../services/theme';
import { SupabaseService } from '../../services/supabase';
import { CreditService } from '../../services/credit';
import { LucideAngularModule, Moon, Sun, Monitor, Palette, Search, Bell, User, LogOut } from 'lucide-angular';
import { RouterLink, RouterLinkActive, Router } from '@angular/router';

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
  router = inject(Router);

  readonly Sun = Sun;
  readonly Moon = Moon;
  readonly Palette = Palette;
  readonly Search = Search;
  readonly Bell = Bell;
  readonly User = User;
  readonly LogOut = LogOut;

  async logout() {
    await this.supabase.signOut();
    this.router.navigate(['/login']);
  }

  getUserName(): string {
    const user = this.supabase.user();
    if (user) {
      // Try to get name from user metadata, fallback to email
      const metadata = user.user_metadata;
      if (metadata?.['full_name']) {
        return metadata['full_name'];
      } else if (metadata?.['name']) {
        return metadata['name'];
      } else if (user.email) {
        return user.email.split('@')[0];
      }
    }
    return 'User';
  }

  getUserInitials(): string {
    const user = this.supabase.user();
    if (user) {
      const metadata = user.user_metadata;
      const fullName = metadata?.['full_name'] || metadata?.['name'] || '';
      if (fullName) {
        const parts = fullName.split(' ');
        if (parts.length >= 2) {
          return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
        }
        return fullName.substring(0, 2).toUpperCase();
      } else if (user.email) {
        return user.email.substring(0, 2).toUpperCase();
      }
    }
    return 'U';
  }

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
