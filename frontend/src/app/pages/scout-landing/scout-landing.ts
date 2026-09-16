import { ChangeDetectionStrategy, Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Meta, Title } from '@angular/platform-browser';
import { ArrowRight, BadgeCheck, ChartNoAxesCombined, History, LucideAngularModule, Search } from 'lucide-angular';

@Component({
  selector: 'app-scout-landing',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, LucideAngularModule],
  templateUrl: './scout-landing.html',
  styleUrl: './scout-landing.css',
})
export class ScoutLandingComponent implements OnInit {
  readonly ArrowRight = ArrowRight;
  readonly BadgeCheck = BadgeCheck;
  readonly ChartNoAxesCombined = ChartNoAxesCombined;
  readonly History = History;
  readonly Search = Search;

  private meta = inject(Meta);
  private title = inject(Title);

  ngOnInit() {
    this.title.setTitle('Domain Scout - Find Better Auction Domains Faster | Scout by Buildomain');

    this.meta.addTags([
      { name: 'description', content: 'Browse, score, and analyze auction domains from GoDaddy, Namecheap, and NameSilo in one workspace. AI-powered investment analysis and SEO enrichment for domain investors.' },
      { property: 'og:title', content: 'Domain Scout - Find Better Auction Domains' },
      { property: 'og:description', content: 'Stop juggling 5 tabs to evaluate one domain. Scout gives you multi-marketplace browsing, investor-weighted scoring, and AI analysis in one place.' },
      { property: 'og:type', content: 'website' },
      { property: 'og:url', content: 'https://scout.buildomain.com' },
      { property: 'og:site_name', content: 'Domain Scout by Buildomain' },
      { name: 'twitter:card', content: 'summary_large_image' },
      { name: 'twitter:title', content: 'Domain Scout - Find Better Auction Domains' },
      { name: 'twitter:description', content: 'Stop juggling 5 tabs to evaluate one domain. Scout gives you multi-marketplace browsing, investor-weighted scoring, and AI analysis in one place.' },
    ]);
  }
}
