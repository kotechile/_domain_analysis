import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { HeaderComponent } from './components/header/header';
import { SidebarComponent } from './components/sidebar/sidebar';
import { LucideAngularModule } from 'lucide-angular';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, HeaderComponent, SidebarComponent, LucideAngularModule, CommonModule],
  template: `
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
  `,
  styles: [`
    :host {
      @apply block;
    }
  `]
})
export class AppComponent {
  title = 'Domain Scout';
}
