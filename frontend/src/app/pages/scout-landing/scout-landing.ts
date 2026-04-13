import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ArrowRight, BadgeCheck, ChartNoAxesCombined, History, LucideAngularModule, Search } from 'lucide-angular';

@Component({
  selector: 'app-scout-landing',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, LucideAngularModule],
  templateUrl: './scout-landing.html',
  styleUrl: './scout-landing.css',
})
export class ScoutLandingComponent {
  readonly ArrowRight = ArrowRight;
  readonly BadgeCheck = BadgeCheck;
  readonly ChartNoAxesCombined = ChartNoAxesCombined;
  readonly History = History;
  readonly Search = Search;
}
