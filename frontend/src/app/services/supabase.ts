import { Injectable, signal } from '@angular/core';
import { createClient, SupabaseClient, User, Session } from '@supabase/supabase-js';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class SupabaseService {
  private supabase: SupabaseClient;

  // Use Angular Signals for state management
  user = signal<User | null>(null);
  session = signal<Session | null>(null);
  loading = signal<boolean>(true);

  constructor() {
    this.supabase = createClient(environment.supabaseUrl, environment.supabaseAnonKey, {
      auth: {
        // Disable LockManager to prevent "immediately failed" warnings
        // This is safe for single-tab usage; multi-tab sync won't work
        lock: undefined
      }
    });

    // Initialize session and set up listener
    this.initSession();

    this.supabase.auth.onAuthStateChange((event, session) => {
      this.session.set(session);
      this.user.set(session?.user ?? null);
      this.loading.set(false);
      console.log('Auth event:', event, 'User:', session?.user?.email);
    });
  }

  private async initSession() {
    const { data: { session } } = await this.supabase.auth.getSession();
    this.session.set(session);
    this.user.set(session?.user ?? null);
    this.loading.set(false);
  }

  async signInWithGoogle() {
    return await this.supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`
      }
    });
  }

  async signOut() {
    await this.supabase.auth.signOut();
  }

  get client() {
    return this.supabase;
  }
}
