import { Routes } from '@angular/router';
import { DomainAnalysisComponent } from './pages/domain-analysis/domain-analysis';
import { MarketplaceComponent } from './pages/marketplace/marketplace';
import { ReportDetailComponent } from './pages/report-detail/report-detail';
import { BillingComponent } from './pages/billing/billing';
import { ThemeShowcaseComponent } from './components/theme-showcase/theme-showcase';

export const routes: Routes = [
    { path: '', component: DomainAnalysisComponent },
    { path: 'marketplace', component: MarketplaceComponent },
    { path: 'reports/:domain', component: ReportDetailComponent },
    { path: 'billing', component: BillingComponent },
    { path: 'themes', component: ThemeShowcaseComponent }
];
