import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class HostService {
  private get hostname(): string {
    return typeof window === 'undefined' ? '' : window.location.hostname.toLowerCase();
  }

  isScoutHost(): boolean {
    return this.hostname === 'scout.buildomain.com' || this.hostname.startsWith('scout.');
  }

  isContentHost(): boolean {
    return this.hostname === 'content.buildomain.com' || this.hostname.startsWith('content.');
  }

  isBuildomainHost(): boolean {
    return this.hostname === 'buildomain.com' || this.hostname === 'www.buildomain.com';
  }

  publicHomePath(): string {
    if (this.isScoutHost()) {
      return '/scout';
    }

    if (this.isContentHost()) {
      return '/content';
    }

    return '/';
  }

  appHomePath(): string {
    return '/app';
  }

  deepAnalysisPath(): string {
    return '/deepanalysis';
  }
}
