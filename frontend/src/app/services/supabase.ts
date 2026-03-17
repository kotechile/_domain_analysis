import { Injectable, signal } from '@angular/core';
import { createClient, SupabaseClient, User, Session } from '@supabase/supabase-js';
import { environment } from '../../environments/environment';

// Custom storage implementation that avoids LockManager issues
// while still persisting to localStorage
const customStorage = {
  getItem: (key: string): string | null => {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  setItem: (key: string, value: string): void => {
    try {
      localStorage.setItem(key, value);
    } catch {
      // Ignore storage errors (e.g., quota exceeded)
    }
  },
  removeItem: (key: string): void => {
    try {
      localStorage.removeItem(key);
    } catch {
      // Ignore storage errors
    }
  }
};

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
        // Use custom storage to avoid LockManager issues
        storage: customStorage,
        storageKey: 'sb-auth-token',
        // Disable auto-refresh to avoid LockManager
        autoRefreshToken: true,
        persistSession: true
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

  async signInWithEmail(email: string, password: string) {
    return await this.supabase.auth.signInWithPassword({
      email,
      password
    });
  }

  async signUpWithEmail(email: string, password: string) {
    return await this.supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`
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
