# Migration Plan: React to Angular 21 (Domain Scout App)

This document outlines the step-by-step process for migrating the Domain Scout SaaS application from React to a modern Angular 21 architecture, leveraging **Signals**, **Standalone Components**, and **Native Control Flow**.

## 🏗️ Architectural Overview

| Feature | React Implementation | Angular 21 Implementation |
| :--- | :--- | :--- |
| **Component Architecture** | Functional Components (TSX) | **Standalone Components** |
| **State Management** | React Context + React Query | **Signals** + **Services** |
| **Data Fetching** | Axios + TanStack Query | **HttpClient** + **RxJS** (as Signals) |
| **UI Library** | Material UI (MUI) | **Angular Material** |
| **Routing** | React Router DOM | **Angular Router** (with `provideRouter`) |
| **Authentication** | Supabase JS SDK | **Supabase JS SDK** in an Angular Service |

---

## 🛠️ Step 1: Framework & Environment Setup

### 1.1 Install Dependencies
In the `/angular-version` directory:
```bash
npm install @supabase/supabase-js @angular/material @angular/cdk lucide-angular axios
```

### 1.2 Configure Supabase Environment
Create a `src/environments/environment.ts` (and `.prod.ts`) to store Supabase credentials, mirroring the React `.env` file.

### 1.3 Update App Config
Register necessary providers in `src/app/app.config.ts`:
- `provideHttpClient()`
- `provideAnimationsAsync()` (for Material)
- `provideRouter(routes)`

---

## 🧠 Step 2: Core Logic Migration (Services)

### 2.1 `SupabaseService`
Migrate `supabaseClient.ts` to a singleton service.
- **Signals**: Use a `user = signal<User | null>(null)` to track authentication state globally.
- **Methods**: Implement `signInWithGoogle()`, `signOut()`, and `getSession()`.

### 2.2 `ApiService`
Refactor the 1400-line `api.tsx` into an Angular service.
- **Typed Models**: Move the extensive interface definitions to `src/app/models/domain.model.ts`.
- **HttpClient**: Replace `axios` with `HttpClient` for better integration with Angular's interceptors.
- **Interceptors**: Create a functional interceptor to inject the Supabase JWT token into outgoing requests.

### 2.3 `CreditService`
A dedicated service for managing user balance and transactions using Signals.
- `balance = signal<number>(0)`
- `refreshBalance()` method.

---

## 🎨 Step 3: UI & Component Migration

### 3.1 Layout & Navigation
- **Header Component**: Migrate `Header.tsx` to a standalone component. Use `@if` for conditional rendering of user profile/login buttons.
- **Protected Routes**: Implement an `authGuard` using the `canActivate` functional guard pattern to replace `ProtectedRoute.tsx`.

### 3.2 Core Components (Signal-First)
- **Marketplace Table**: Migrate `AuctionsTable.tsx`. Use the new `@for` syntax with `track` for high-performance rendering of domain lists.
- **Analysis Progress**: Migrate `AnalysisProgress.tsx`. Use a signal to track the `progressPercentage` and update the view reactively.
- **Historical Chart**: Migrate `HistoricalDataChart.tsx`. Leverage `ngx-charts` or `Chart.js` with Angular wrappers.

---

## 📄 Step 4: Page Re-composition

### 4.1 Domain Analysis (Home)
Migrate `DomainAnalysisPage.tsx`.
- **Form Handling**: Use **Reactive Forms**.
- **State**: Use a signal for the `domainName` input and `analysisLoading` status.

### 4.2 Reports & Detailed Analysis
Migrate `ReportPage.tsx` and `ReportsListPage.tsx`.
- **Route Params**: Use `inject(ActivatedRoute)` to get domain names from the URL.
- **Computed Signals**: Use `computed()` to derive SEO health scores or display formatting from the raw report data.

---

## 🚀 Step 5: Optimization with Angular 21 Features

- **Signals for State**: Replace all `useState`/`useEffect` patterns from React with `signal()`, `computed()`, and `effect()`.
- **Deferrable Views**: Use `@defer` in templates for heavy components like charts or complex tables to improve Initial Page Load.
- **Hydration**: If deploying to a server, enable **Incremental Hydration** for better SEO (critical for a domain analysis tool).

---

## 📅 Roadmap (Estimated 2 Weeks)
1. **Days 1-2**: Base configuration, Auth Service, and API layer.
2. **Days 3-5**: Core UI Shell (Navigation, Theme, Guards).
3. **Days 6-10**: Migration of complex tables (Auctions, Marketplace) and Charts.
4. **Days 11-14**: Refinement, Animation, and Performance Tuning.
