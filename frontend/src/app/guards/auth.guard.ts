import { Injectable, inject } from '@angular/core';
import { CanActivate, Router, UrlTree } from '@angular/router';
import { SupabaseService } from '../services/supabase';

@Injectable({
  providedIn: 'root'
})
export class AuthGuard implements CanActivate {
  private supabase = inject(SupabaseService);
  private router = inject(Router);

  canActivate(): boolean | UrlTree {
    const user = this.supabase.user();
    if (user) {
      return true;
    }
    return this.router.createUrlTree(['/login']);
  }
}
