import { Injectable, signal } from '@angular/core';
import { createClient, SupabaseClient, User, Session } from '@supabase/supabase-js';
import { environment } from '../../environments/environment';

// Custom lock function that bypasses Navigator LockManager
// Supabase expects: lock(name: string, timeout: number, callback: () => Promise<T>): Promise<T>
const customLock = async <T>(
  name: string,
  timeout: number,
  callback: () => Promise<T>
): Promise<T> => {
  // Immediately execute the callback without actual locking
  // This bypasses the Navigator LockManager entirely
  return await callback();
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
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
        // Use a fresh storage key to ignore old "stuck" locks
        storageKey: 'scout-dna-v1',
        // Use custom lock to bypass Navigator LockManager
        lock: customLock
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
