import { Component, Input, OnInit, OnDestroy, AfterViewInit, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Chart, ChartConfiguration, ChartData, ChartType } from 'chart.js';
import { HistoricalMetricPoint } from '../../models/domain.model';

@Component({
  selector: 'app-traffic-chart',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="w-full h-full">
      <canvas #chartCanvas></canvas>
    </div>
  `,
  styles: [`
    :host {
      @apply block w-full h-full;
    }
  `]
})
export class TrafficChartComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('chartCanvas') chartCanvas!: ElementRef<HTMLCanvasElement>;
  @Input() trafficData: HistoricalMetricPoint[] = [];
  @Input() title: string = 'Organic Traffic History';

  private chart: Chart | null = null;

  ngOnInit() {}

  ngAfterViewInit() {
    this.createChart();
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

    // Sort data by date
    const sortedData = [...this.trafficData].sort((a, b) =>
      new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    // Format dates for display
    const labels = sortedData.map(point => {
      const date = new Date(point.date);
      return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
    });

    const data = sortedData.map(point => point.value);

    // Get computed accent color from CSS variable
    const accentColor = getComputedStyle(document.documentElement).getPropertyValue('--accent-color').trim();
    const accentRgb = getComputedStyle(document.documentElement).getPropertyValue('--accent-color-rgb').trim();

    // Create gradient using the RGB values
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
            backgroundColor: 'var(--card-bg)',
            titleColor: 'var(--text-color)',
            bodyColor: 'var(--text-color)',
            borderColor: 'var(--border-color)',
            borderWidth: 1,
            padding: 12,
            displayColors: false,
            callbacks: {
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
              font: {
                size: 10,
              },
              callback: (value) => {
                const num = Number(value);
                if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
                if (num >= 1000) return (num / 1000).toFixed(0) + 'K';
                return num.toString();
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
    if (this.chart) {
      this.chart.destroy();
    }
    this.createChart();
  }
}
