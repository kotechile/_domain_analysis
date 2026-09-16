import { ChangeDetectionStrategy, Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Meta, Title } from '@angular/platform-browser';
import { LucideAngularModule, Check, Zap, Crown, ArrowRight, CreditCard, Star } from 'lucide-angular';

@Component({
  selector: 'app-pricing',
  standalone: true,
  imports: [RouterLink, LucideAngularModule],
  templateUrl: './pricing.html',
  styleUrl: './pricing.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PricingComponent implements OnInit {
  readonly Check = Check;
  readonly Zap = Zap;
  readonly Crown = Crown;
  readonly ArrowRight = ArrowRight;
  readonly CreditCard = CreditCard;
  readonly Star = Star;

  readonly creditPacks = [
    { credits: 50, price: 5, label: 'Starter Pack', description: 'Perfect for trying Scout' },
    { credits: 250, price: 20, label: 'Pro Bundle', description: 'Most popular choice', popular: true },
    { credits: 1000, price: 75, label: 'Enterprise Scout', description: 'For heavy researchers' },
  ];

  private meta = inject(Meta);
  private title = inject(Title);

  ngOnInit() {
    this.title.setTitle('Pricing - Domain Scout by Buildomain');

    this.meta.addTags([
      { name: 'description', content: 'Simple, transparent pricing for Domain Scout. Start free, upgrade when you need more analysis power. Pro plans from $19/mo.' },
      { property: 'og:title', content: 'Pricing - Domain Scout' },
      { property: 'og:description', content: 'Start free, upgrade when ready. Pro plans from $19/mo with 200 credits, or go unlimited with Agency at $49/mo.' },
      { property: 'og:type', content: 'website' },
      { property: 'og:url', content: 'https://scout.buildomain.com/pricing' },
      { name: 'twitter:card', content: 'summary' },
      { name: 'twitter:title', content: 'Pricing - Domain Scout' },
      { name: 'twitter:description', content: 'Start free, upgrade when ready. Pro plans from $19/mo.' },
    ]);
  }
}