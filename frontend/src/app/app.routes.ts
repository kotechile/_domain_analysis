import { Routes } from '@angular/router';
import { DomainAnalysisComponent } from './pages/domain-analysis/domain-analysis';
import { MarketplaceComponent } from './pages/marketplace/marketplace';
import { ReportDetailComponent } from './pages/report-detail/report-detail';
import { BillingComponent } from './pages/billing/billing';
import { ThemeShowcaseComponent } from './components/theme-showcase/theme-showcase';
import { LoginComponent } from './pages/login/login';
import { AuthCallbackComponent } from './pages/auth-callback/auth-callback';
import { AuthGuard } from './guards/auth.guard';
import { ReportsListComponent } from './pages/reports-list/reports-list';
import { ImportComponent } from './pages/import/import';

export const routes: Routes = [
    { path: 'login', component: LoginComponent },
    { path: 'auth/callback', component: AuthCallbackComponent },
    { path: '', component: DomainAnalysisComponent, canActivate: [AuthGuard] },
    { path: 'marketplace', component: MarketplaceComponent, canActivate: [AuthGuard] },
    { path: 'import', component: ImportComponent, canActivate: [AuthGuard] },
    { path: 'reports', component: ReportsListComponent, canActivate: [AuthGuard] },
    { path: 'reports/:domain', component: ReportDetailComponent, canActivate: [AuthGuard] },
    { path: 'billing', component: BillingComponent, canActivate: [AuthGuard] },
    { path: 'themes', component: ThemeShowcaseComponent, canActivate: [AuthGuard] }
];
