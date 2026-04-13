import { Component } from '@angular/core';

@Component({
  selector: 'app-terms',
  standalone: true,
  template: `
    <div class="min-h-screen py-20 px-8 max-w-3xl mx-auto" style="color: var(--text-color)">
        <h1 class="text-4xl font-black mb-6">Terms of Service</h1>
        <p class="mb-10 opacity-50 text-sm">Last Updated: April 2026</p>
        
        <div class="space-y-8">
            <section>
                <h2 class="text-xl font-bold mb-3">1. Assumption of Risk & Liability Limitation</h2>
                <p class="text-sm opacity-80 leading-relaxed">
                    Scout provides aggregated SEO metrics, historical data, and AI analysis for expired and auctioned domains. 
                    <strong>This data is provided "AS IS" for informational purposes only.</strong> We do not guarantee the accuracy, 
                    completeness, or reliability of any metrics. Domain acquisition involves significant inherent risk. Under no 
                    circumstances shall Scout be held liable for any financial losses, traffic drops, search engine penalties, 
                    or other damages resulting from domain purchases influenced by our reports.
                </p>
            </section>

            <section>
                <h2 class="text-xl font-bold mb-3">2. Third-Party Data Sources</h2>
                <p class="text-sm opacity-80 leading-relaxed">
                    Our reports rely on third-party APIs (including but not limited to Ahrefs, Majestic, and the Internet Archive). 
                    Availability and accuracy of these metrics are subject to the respective third-party providers. We do not own 
                    this data and are not responsible for discrepancies between our reports and live search engine behavior.
                </p>
            </section>

            <section>
                <h2 class="text-xl font-bold mb-3">3. Credit System & Refunds</h2>
                <p class="text-sm opacity-80 leading-relaxed">
                    Generating Deep Analysis reports consumes credits, which pay for underlying infrastructure and proprietary AI 
                    computations. Credits are non-refundable once a report is successfully generated.
                </p>
            </section>
        </div>
    </div>
  `
})
export class TermsComponent {}
