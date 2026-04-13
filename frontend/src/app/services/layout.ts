import { Injectable, signal, effect } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class LayoutService {
  // Sidebar expanded state tracking (for desktop >768px). Default is expanded.
  private readonly SIDEBAR_EXPANDED_KEY = 'scout_sidebar_expanded';
  
  isSidebarExpanded = signal<boolean>(true);

  constructor() {
    // Initialize from local storage if available
    const saved = localStorage.getItem(this.SIDEBAR_EXPANDED_KEY);
    if (saved !== null) {
      this.isSidebarExpanded.set(saved === 'true');
    }

    // Effect to auto-save any changes to localStorage
    effect(() => {
      localStorage.setItem(this.SIDEBAR_EXPANDED_KEY, String(this.isSidebarExpanded()));
    });
  }

  toggleSidebar() {
    this.isSidebarExpanded.update(v => !v);
  }
}
