import { Component, Input, OnInit, OnDestroy, AfterViewInit, ElementRef, ViewChild, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Chart, ChartConfiguration, ChartData, ChartType, registerables } from 'chart.js';
import { HistoricalMetricPoint } from '../../models/domain.model';

// Register Chart.js components
Chart.register(...registerables);

@Component({
  selector: 'app-traffic-chart',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="w-full h-full min-h-[300px]">
      <canvas #chartCanvas></canvas>
    </div>
  `,
  styles: [`
    :host {
      @apply block w-full h-full;
    }
  `]
})
export class TrafficChartComponent implements OnInit, AfterViewInit, OnChanges, OnDestroy {
  @ViewChild('chartCanvas') chartCanvas!: ElementRef<HTMLCanvasElement>;
  @Input() trafficData: HistoricalMetricPoint[] = [];
  @Input() title: string = 'Organic Traffic History';

  private chart: Chart | null = null;

  private parseTrafficDate(rawDate: string): Date | null {
    if (!rawDate) return null;

    const parsed = new Date(rawDate);
    if (!Number.isNaN(parsed.getTime())) {
      return parsed;
    }

    const normalized = String(rawDate).trim();

    // Recover compact year/month values such as 20202 -> 2020-02-01 or 202004 -> 2020-04-01.
    const compactMatch = normalized.match(/^(\d{4})(\d{1,2})$/);
    if (compactMatch) {
      const [, year, month] = compactMatch;
      const compactDate = new Date(`${year}-${month.padStart(2, '0')}-01`);
      if (!Number.isNaN(compactDate.getTime())) {
        return compactDate;
      }
    }

    // Recover bare years such as 2025 -> 2025-01-01.
    const yearOnlyMatch = normalized.match(/^(\d{4})$/);
    if (yearOnlyMatch) {
      const yearDate = new Date(`${normalized}-01-01`);
      if (!Number.isNaN(yearDate.getTime())) {
        return yearDate;
      }
    }

    return null;
  }

  ngOnInit() {}

  ngOnChanges(changes: SimpleChanges) {
    if (changes['trafficData'] && !changes['trafficData'].firstChange) {
      this.createChart();
    }
  }

  ngAfterViewInit() {
    // Small delay to ensure container size is calculated
    setTimeout(() => this.createChart(), 0);
  }

  ngOnDestroy() {
    if (this.chart) {
      this.chart.destroy();
    }
  }

  private createChart() {
    if (!this.chartCanvas?.nativeElement || !this.trafficData?.length) {
      return;
    }

    const ctx = this.chartCanvas.nativeElement.getContext('2d');
    if (!ctx) return;

    // Destroy existing chart
    if (this.chart) {
      this.chart.destroy();
    }

    // Sort data by date
    const sortedData = [...this.trafficData].sort((a, b) => {
      const left = this.parseTrafficDate(a.date)?.getTime() ?? 0;
      const right = this.parseTrafficDate(b.date)?.getTime() ?? 0;
      return left - right;
    });

    // Format dates for display
    const labels = sortedData.map(point => {
      const date = this.parseTrafficDate(point.date);
      if (!date) return point.date;
      return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    });

    const data = sortedData.map(point => point.value);

    // Get computed accent color from CSS variable
    const rootStyle = getComputedStyle(document.documentElement);
    const accentColor = rootStyle.getPropertyValue('--accent-color').trim() || '#475569';
    let accentRgb = rootStyle.getPropertyValue('--accent-color-rgb').trim();
    
    // Handle space-separated RGB values (e.g. "71 85 105") and convert to comma-separated
    if (accentRgb && !accentRgb.includes(',')) {
      accentRgb = accentRgb.split(' ').join(', ');
    } else if (!accentRgb) {
      accentRgb = '71, 85, 105'; // Default fallback
    }

    // Create gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, `rgba(${accentRgb}, 0.3)`);
    gradient.addColorStop(1, `rgba(${accentRgb}, 0.0)`);

    const config: ChartConfiguration = {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Organic Traffic',
          data,
          borderColor: accentColor,
          backgroundColor: gradient,
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          pointHoverRadius: 4,
          pointHoverBackgroundColor: accentColor,
          pointHoverBorderColor: '#fff',
          pointHoverBorderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          intersect: false,
          mode: 'index',
        },
        plugins: {
          legend: {
            display: false,
          },
          title: {
            display: true,
            text: this.title,
            color: 'var(--text-color)',
            font: {
              size: 12,
              weight: 'bold',
              family: 'system-ui, -apple-system, sans-serif',
            },
            padding: {
              top: 10,
              bottom: 20,
            },
          },
          tooltip: {
            backgroundColor: 'rgba(30, 41, 59, 0.9)', // Muted dark background
            titleColor: '#fff',
            bodyColor: '#fff',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1,
            padding: 12,
            displayColors: false,
            callbacks: {
              title: (tooltipItems) => {
                const rawLabel = tooltipItems[0]?.label;
                return rawLabel || 'Unknown date';
              },
              label: (context) => {
                const value = context.parsed.y;
                if (value == null) return 'Traffic: N/A';
                return `Traffic: ${value.toLocaleString()}`;
              },
            },
          },
        },
        scales: {
          x: {
            display: true,
            grid: {
              display: false,
            },
            ticks: {
              color: 'rgba(128, 128, 128, 0.5)',
              maxTicksLimit: 12,
              maxRotation: 0,
              font: {
                size: 10,
              },
            },
          },
          y: {
            display: true,
            grid: {
              color: 'rgba(128, 128, 128, 0.1)',
            },
            ticks: {
              color: 'rgba(128, 128, 128, 0.5)',
              maxTicksLimit: 8,
              font: {
                size: 10,
              },
              callback: (value) => {
                const num = Number(value);
                if (num >= 1000000) {
                  return (num / 1000000).toLocaleString(undefined, { maximumFractionDigits: 1 }) + 'M';
                }
                if (num >= 1000) {
                  return (num / 1000).toLocaleString(undefined, { maximumFractionDigits: 1 }) + 'K';
                }
                return num.toLocaleString();
              },
            },
          },
        },
      },
    };

    this.chart = new Chart(ctx, config);
  }

  // Update chart when data changes
  updateChart(trafficData: HistoricalMetricPoint[]) {
    this.trafficData = trafficData;
    this.createChart();
  }
}
