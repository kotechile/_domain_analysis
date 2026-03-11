import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ThemeService } from '../../services/theme';

@Component({
  selector: 'app-theme-showcase',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="space-y-12">
      <div class="text-center">
        <h1 class="text-5xl font-black mb-4" style="color: var(--text-color)">Visual Theme Verification</h1>
        <p class="text-lg opacity-70" style="color: var(--text-color)">Testing contrast across all four modes.</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
        <!-- Dashboard Card Mockup -->
        <div class="card space-y-4">
          <div class="flex justify-between items-center">
            <h3 class="font-bold text-xl">SaaS Analytics</h3>
            <span class="px-3 py-1 rounded-full text-xs font-bold" style="background: var(--accent-color); color: white">Active</span>
          </div>
          <p class="opacity-60 text-sm">Real-time domain scanning performance across global nodes.</p>
          <div class="h-40 rounded-lg flex items-end justify-between px-2 pb-2 transition-all" style="background: var(--bg-color); border: 1px solid var(--border-color)">
             <div class="w-8 h-1/2 rounded-t" style="background: var(--accent-color)"></div>
             <div class="w-8 h-3/4 rounded-t opacity-90" style="background: var(--accent-color)"></div>
             <div class="w-8 h-1/4 rounded-t opacity-80" style="background: var(--accent-color)"></div>
             <div class="w-8 h-full rounded-t opacity-70" style="background: var(--accent-color)"></div>
             <div class="w-8 h-3/4 rounded-t opacity-60" style="background: var(--accent-color)"></div>
          </div>
        </div>

        <!-- Metric Cards -->
        <div class="grid grid-cols-2 gap-4">
          <div class="card text-center flex flex-col justify-center">
             <span class="text-3xl font-black" style="color: var(--accent-color)">1.2k</span>
             <span class="text-xs uppercase font-bold tracking-widest opacity-50">Domains Scanned</span>
          </div>
          <div class="card text-center flex flex-col justify-center">
             <span class="text-3xl font-black" style="color: var(--accent-color)">98%</span>
             <span class="text-xs uppercase font-bold tracking-widest opacity-50">Accuracy</span>
          </div>
          <div class="card text-center flex flex-col justify-center">
             <span class="text-3xl font-black" style="color: var(--accent-color)">0.4s</span>
             <span class="text-xs uppercase font-bold tracking-widest opacity-50">Avg Latency</span>
          </div>
          <div class="card text-center flex flex-col justify-center" style="background: var(--accent-color)">
             <span class="text-3xl font-black text-white">PRO</span>
             <span class="text-xs uppercase font-bold tracking-widest text-white opacity-80">Tier Active</span>
          </div>
        </div>
      </div>

      <!-- Contrast Check Table -->
      <div class="card overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="uppercase opacity-50 font-bold border-b" style="border-color: var(--border-color)">
            <tr>
              <th class="pb-4">Element</th>
              <th class="pb-4">Standard Mode Value</th>
              <th class="pb-4">High Contrast (+) Value</th>
            </tr>
          </thead>
          <tbody class="divide-y" style="divide-color: var(--border-color)">
            <tr>
              <td class="py-4 font-semibold">Background</td>
              <td class="py-4">#F8F9FA / #1A1D21</td>
              <td class="py-4 font-bold" style="color: var(--accent-color)">#FFFFFF / #000000</td>
            </tr>
            <tr>
              <td class="py-4 font-semibold">Text Primary</td>
              <td class="py-4">#495057 / #ADB5BD</td>
              <td class="py-4 font-bold" style="color: var(--accent-color)">Pure Black / Pure White</td>
            </tr>
            <tr>
              <td class="py-4 font-semibold">Accent</td>
              <td class="py-4">Stone Gray / Steel Blue</td>
              <td class="py-4 font-bold uppercase" style="color: var(--accent-color)">Vibrant Primary</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `
})
export class ThemeShowcaseComponent {
  themeService = inject(ThemeService);
}
