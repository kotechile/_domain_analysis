import { Injectable, signal, effect, inject } from '@angular/core';
import { SupabaseService } from './supabase';

export type ThemeMode = 'light-modern' | 'light-plus' | 'dark-modern' | 'dark-plus';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  private supabase = inject(SupabaseService);

  // Reactive Signal for the current theme
  currentTheme = signal<ThemeMode>('light-modern');

  constructor() {
    // 1. Initial Load from LocalStorage
    const savedTheme = localStorage.getItem('app-theme') as ThemeMode;
    if (savedTheme) {
      this.currentTheme.set(savedTheme);
      this.applyTheme(savedTheme);
    }

    // 2. React to Auth status to sync with Profile API
    effect(() => {
      const user = this.supabase.user();
      if (user) {
        this.fetchProfileTheme();
      }
    });

    // 3. Reactively apply theme and save to LocalStorage
    effect(() => {
      const theme = this.currentTheme();
      this.applyTheme(theme);
      localStorage.setItem('app-theme', theme);

      // Sync with API if user is logged in
      this.syncThemeToProfile(theme);
    });
  }

  setTheme(theme: ThemeMode) {
    this.currentTheme.set(theme);
  }

  private applyTheme(theme: ThemeMode) {
    const root = document.documentElement;
    root.setAttribute('data-theme', theme);

    // Toggle Tailwind dark mode class
    if (theme.startsWith('dark')) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }

  private async fetchProfileTheme() {
    const { data, error } = await this.supabase.client
      .from('user_profiles')
      .select('theme_preference')
      .single();

    if (data?.theme_preference) {
      this.currentTheme.set(data.theme_preference as ThemeMode);
    }
  }

  private async syncThemeToProfile(theme: ThemeMode) {
    const user = this.supabase.user();
    if (!user) return;

    await this.supabase.client
      .from('user_profiles')
      .upsert({
        id: user.id,
        theme_preference: theme,
        updated_at: new Date()
      });
  }
}
