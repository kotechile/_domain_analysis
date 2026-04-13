import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { SupabaseService } from '../../services/supabase';
import { HostService } from '../../services/host';

@Component({
  selector: 'app-auth-callback',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="min-h-screen flex items-center justify-center"
         style="background: var(--bg-color); color: var(--text-color)">
      <div class="text-center space-y-4">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4 animate-pulse"
             style="background: var(--accent-color)">
          <span class="text-2xl font-black text-white">S</span>
        </div>
        <h1 class="text-xl font-black tracking-tight" style="color: var(--text-color)">
          Completing Sign In...
        </h1>
        <p class="text-sm opacity-60" style="color: var(--text-color)">
          Please wait while we verify your credentials.
        </p>

        @if (error()) {
        <div class="mt-6 p-4 rounded-xl text-sm font-medium max-w-md mx-auto"
             style="background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2)">
          {{ error() }}
          <div class="mt-4">
            <button
              (click)="goToLogin()"
              class="px-6 py-2 rounded-xl font-bold text-xs uppercase tracking-widest transition-all"
              style="background: var(--accent-color); color: white">
              Back to Login
            </button>
          </div>
        </div>
        }
      </div>
    </div>
  `,
  styles: [`
    :host {
      @apply block;
    }
  `]
})
export class AuthCallbackComponent implements OnInit {
  private supabase = inject(SupabaseService);
  private router = inject(Router);
  private hostService = inject(HostService);

  error = signal('');

  async ngOnInit() {
    // Handle the OAuth callback
    // Supabase automatically handles the URL hash fragment
    const { data: { session }, error } = await this.supabase.client.auth.getSession();

    if (error) {
      console.error('Auth callback error:', error);
      this.error.set('Authentication failed. Please try again.');
      return;
    }

    if (session) {
      this.router.navigateByUrl(this.hostService.appHomePath());
    } else {
      const hash = window.location.hash;
      if (hash) {
        setTimeout(async () => {
          const { data: { session: retrySession } } = await this.supabase.client.auth.getSession();
          if (retrySession) {
            this.router.navigateByUrl(this.hostService.appHomePath());
          } else {
            this.error.set('Authentication incomplete. Please try again.');
          }
        }, 1000);
      } else {
        this.error.set('No authentication data found. Please try again.');
      }
    }
  }

  goToLogin() {
    this.router.navigateByUrl(this.hostService.isBuildomainHost() ? '/' : '/login');
  }
}
