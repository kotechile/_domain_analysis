// Runtime environment configuration
// Falls back to build-time values if runtime config not available

interface RuntimeEnv {
    production: boolean;
    apiUrl: string;
    supabaseUrl: string;
    supabaseAnonKey: string;
    appUrl: string;
}

declare global {
    interface Window {
        __env?: {
            supabaseUrl?: string;
            supabaseAnonKey?: string;
            apiUrl?: string;
            appUrl?: string;
        };
    }
}

// Default values (build-time fallbacks)
const defaultEnv: RuntimeEnv = {
    production: true,
    apiUrl: '/api/v1',
    supabaseUrl: 'https://sbdomain.buildomain.com',
    supabaseAnonKey: '',
    appUrl: 'https://scout.buildomain.com'
};

// Merge runtime config with defaults
const runtimeEnv = window.__env || {};

export const environment: RuntimeEnv = {
    production: defaultEnv.production,
    apiUrl: runtimeEnv.apiUrl || defaultEnv.apiUrl,
    supabaseUrl: runtimeEnv.supabaseUrl || defaultEnv.supabaseUrl,
    supabaseAnonKey: runtimeEnv.supabaseAnonKey || defaultEnv.supabaseAnonKey,
    appUrl: runtimeEnv.appUrl || defaultEnv.appUrl
};
