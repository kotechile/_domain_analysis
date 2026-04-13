import { ChangeDetectionStrategy, Component, computed, effect, inject } from '@angular/core';
import { RouterOutlet, Router } from '@angular/router';
import { HeaderComponent } from './components/header/header';
import { SidebarComponent } from './components/sidebar/sidebar';
import { LucideAngularModule } from 'lucide-angular';
import { SupabaseService } from './services/supabase';
import { HostService } from './services/host';

@Component({
  selector: 'app-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, HeaderComponent, SidebarComponent, LucideAngularModule],
  template: `
    @if (isAppRoute() && isLoading()) {
      <!-- Loading State -->
      <div class="min-h-screen flex items-center justify-center"
           style="background: var(--bg-color); color: var(--text-color)">
        <div class="text-center space-y-4">
          <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4 animate-pulse"
               style="background: var(--accent-color)">
            <span class="text-2xl font-black text-white">S</span>
          </div>
          <h1 class="text-xl font-black tracking-tight" style="color: var(--text-color)">
            Loading...
          </h1>
        </div>
      </div>
    } @else if (isAppRoute() && isAuthenticated()) {
      <div class="min-h-screen transition-all duration-500"
           style="background: var(--bg-color); color: var(--text-color)">

        <!-- Global Navigation Shell -->
        <app-sidebar />
        <app-header />

        <!-- Main Content Area (Offset for Sidebar) -->
        <main class="transition-all duration-500" style="margin-left: 16rem; min-height: calc(100vh - 80px)">
          <div class="animate-in fade-in duration-1000">
            <router-outlet />
          </div>

          <!-- Premium Footer -->
          <footer class="mt-24 py-12 border-t border-opacity-5 text-center px-10"
                  style="border-color: var(--border-color)">
            <div class="flex flex-col items-center space-y-4">
               <div class="flex items-center space-x-2">
                  <span class="text-xs font-black tracking-widest opacity-20 uppercase" style="color: var(--text-color)">Built for SaaS Domain Scouters</span>
               </div>
               <p class="text-[10px] font-bold opacity-30 uppercase tracking-[0.3em]" style="color: var(--text-color)">
                 &copy; 2026 Kotechile • Built with Angular & Supabase
               </p>
            </div>
          </footer>
        </main>
      </div>
    } @else {
      <router-outlet />
    }
  `,
  styles: [`
    :host {
      @apply block;
    }
  `]
})
export class AppComponent {
  private supabase = inject(SupabaseService);
  private router = inject(Router);
  private hostService = inject(HostService);

  isAuthenticated = computed(() => !!this.supabase.user());
  isLoading = this.supabase.loading;
  isAppRoute = computed(() =>
    this.router.url === '/app' ||
    this.router.url.startsWith('/app/') ||
    this.router.url === '/deepanalysis' ||
    this.router.url.startsWith('/deepanalysis?')
  );

  constructor() {
    effect(() => {
      const user = this.supabase.user();
      const loading = this.supabase.loading();
      const url = this.router.url;

      if (loading) {
        return;
      }

      if (this.hostService.isBuildomainHost() && url === '/login') {
        this.router.navigateByUrl('/');
        return;
      }

      if (this.hostService.isScoutHost() && url === '/') {
        this.router.navigateByUrl('/scout');
        return;
      }

      if (this.hostService.isContentHost() && url === '/') {
        this.router.navigateByUrl('/content');
        return;
      }

      if (user && url === '/login') {
        this.router.navigateByUrl(this.hostService.appHomePath());
      }
    });
  }
}
