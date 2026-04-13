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
import { BuildomainHomeComponent } from './pages/buildomain-home/buildomain-home';
import { ScoutLandingComponent } from './pages/scout-landing/scout-landing';
import { ContentLandingComponent } from './pages/content-landing/content-landing';

export const routes: Routes = [
    { path: '', component: BuildomainHomeComponent },
    { path: 'scout', component: ScoutLandingComponent },
    { path: 'content', component: ContentLandingComponent },
    { path: 'login', component: LoginComponent },
    { path: 'auth/callback', component: AuthCallbackComponent },
    { path: 'app', component: MarketplaceComponent, canActivate: [AuthGuard] },
    { path: 'deepanalysis', component: DomainAnalysisComponent, canActivate: [AuthGuard] },
    { path: 'app/deepanalysis', redirectTo: 'deepanalysis', pathMatch: 'full' },
    { path: 'app/marketplace', redirectTo: 'app', pathMatch: 'full' },
    { path: 'app/import', component: ImportComponent, canActivate: [AuthGuard] },
    { path: 'app/reports', component: ReportsListComponent, canActivate: [AuthGuard] },
    { path: 'app/reports/:domain', component: ReportDetailComponent, canActivate: [AuthGuard] },
    { path: 'app/billing', component: BillingComponent, canActivate: [AuthGuard] },
    { path: 'app/themes', component: ThemeShowcaseComponent, canActivate: [AuthGuard] },
    { path: 'marketplace', redirectTo: 'app', pathMatch: 'full' },
    { path: 'import', redirectTo: 'app/import', pathMatch: 'full' },
    { path: 'reports', redirectTo: 'app/reports', pathMatch: 'full' },
    { path: 'reports/:domain', redirectTo: 'app/reports/:domain', pathMatch: 'full' },
    { path: 'billing', redirectTo: 'app/billing', pathMatch: 'full' },
    { path: 'themes', redirectTo: 'app/themes', pathMatch: 'full' }
];
