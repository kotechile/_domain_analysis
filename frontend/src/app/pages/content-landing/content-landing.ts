import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ArrowLeft, FileText, LucideAngularModule, Sparkles } from 'lucide-angular';

@Component({
  selector: 'app-content-landing',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, LucideAngularModule],
  templateUrl: './content-landing.html',
  styleUrl: './content-landing.css',
})
export class ContentLandingComponent {
  readonly ArrowLeft = ArrowLeft;
  readonly FileText = FileText;
  readonly Sparkles = Sparkles;
}
