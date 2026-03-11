import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { SupabaseService } from '../services/supabase';
import { from, switchMap, catchError, of } from 'rxjs';

/**
 * Interceptor to inject Supabase JWT token into outgoing API requests
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
    const supabase = inject(SupabaseService);
    const session = supabase.session();

    // If we have a session, inject the token
    if (session?.access_token) {
        const authReq = req.clone({
            setHeaders: {
                Authorization: `Bearer ${session.access_token}`
            }
        });
        return next(authReq);
    }

    // If no session is in memory, double check the client directly 
    // (useful for edge cases during initial load)
    return from(supabase.client.auth.getSession()).pipe(
        switchMap(({ data }) => {
            const token = data.session?.access_token;
            if (token) {
                const authReq = req.clone({
                    setHeaders: {
                        Authorization: `Bearer ${token}`
                    }
                });
                return next(authReq);
            }
            return next(req);
        }),
        catchError(() => next(req))
    );
};
