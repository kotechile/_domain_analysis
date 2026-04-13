import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { BuildomainHomeComponent } from '../buildomain-home/buildomain-home';
import { ScoutLandingComponent } from '../scout-landing/scout-landing';
import { ContentLandingComponent } from '../content-landing/content-landing';
import { HostService } from '../../services/host';

@Component({
  selector: 'app-host-home',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BuildomainHomeComponent, ScoutLandingComponent, ContentLandingComponent],
  template: `
    @if (hostService.isScoutHost()) {
      <app-scout-landing />
    } @else if (hostService.isContentHost()) {
      <app-content-landing />
    } @else {
      <app-buildomain-home />
    }
  `
})
export class HostHomeComponent {
  protected hostService = inject(HostService);
}
