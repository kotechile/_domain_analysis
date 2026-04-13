import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ArrowRight, Compass, FileText, LucideAngularModule } from 'lucide-angular';

@Component({
  selector: 'app-buildomain-home',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, LucideAngularModule],
  templateUrl: './buildomain-home.html',
  styleUrl: './buildomain-home.css',
})
export class BuildomainHomeComponent {
  readonly ArrowRight = ArrowRight;
  readonly Compass = Compass;
  readonly FileText = FileText;
}
