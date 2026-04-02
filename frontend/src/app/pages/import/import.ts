import { Component, inject, signal, OnInit, OnDestroy } from '@angular/core';
import { CommonModule, DatePipe, DecimalPipe, TitleCasePipe } from '@angular/common';
import { ApiService } from '../../services/api';
import { LucideAngularModule, Database, Upload, Activity, CheckCircle, Clock, XCircle, AlertTriangle, RefreshCcw, LayoutDashboard, ChevronRight, Sparkles } from 'lucide-angular';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { interval, Subscription, of } from 'rxjs';
import { switchMap, catchError } from 'rxjs/operators';
import { AuctionUploadProgress } from '../../models/domain.model';

@Component({
  selector: 'app-import',
  standalone: true,
  imports: [CommonModule, LucideAngularModule, MatSnackBarModule, DatePipe, DecimalPipe, TitleCasePipe],
  templateUrl: './import.html',
  styles: [``]
})
export class ImportComponent implements OnInit, OnDestroy {
  private api = inject(ApiService);
  private snackBar = inject(MatSnackBar);
  
  // Icons
  readonly Database = Database;
  readonly Upload = Upload;
  readonly Activity = Activity;
  readonly CheckCircle = CheckCircle;
  readonly Clock = Clock;
  readonly XCircle = XCircle;
  readonly AlertTriangle = AlertTriangle;
  readonly RefreshCcw = RefreshCcw;
  readonly LayoutDashboard = LayoutDashboard;
  readonly ChevronRight = ChevronRight;
  readonly Sparkles = Sparkles;

  // State
  activeJob = signal<AuctionUploadProgress | null>(null);
  isLoading = signal<boolean>(true);
  autoRefreshSub?: Subscription;

  ngOnInit() {
    this.fetchLatestJob();
    
    // Start auto-refresh interval (every 5 seconds)
    this.autoRefreshSub = interval(5000).pipe(
      switchMap(() => {
        return this.api.getLatestActiveUploadProgress().pipe(
          catchError(() => of(null))
        );
      })
    ).subscribe((progress: AuctionUploadProgress | null) => {
      if (progress) {
        this.activeJob.set(progress);
      } else {
        // If we had a job and now its not returned (either finished or error)
        // Check manually one last time
        if (this.activeJob() && this.activeJob()?.status !== 'completed' && this.activeJob()?.status !== 'failed') {
          this.fetchLatestJob();
        }
      }
      this.isLoading.set(false);
    });
  }

  ngOnDestroy() {
    this.autoRefreshSub?.unsubscribe();
  }

  fetchLatestJob() {
    this.isLoading.set(true);
    this.api.getLatestActiveUploadProgress().pipe(
      catchError(() => of(null))
    ).subscribe((progress: AuctionUploadProgress | null) => {
      this.activeJob.set(progress);
      this.isLoading.set(false);
    });
  }

  markAsFailed(jobId: string) {
    if (confirm('Are you sure you want to mark this job as failed? Use this only if the job is truly stuck (e.g. "waiting_for_lock" for more than 1 hour).')) {
      this.api.markUploadJobAsFailed(jobId).subscribe({
        next: () => {
          this.snackBar.open('Job marked as failed manually', 'Close', { duration: 3000 });
          this.fetchLatestJob();
        },
        error: (err: any) => {
          this.snackBar.open('Failed to mark job as failed', 'Close', { duration: 3000 });
        }
      });
    }
  }

  triggerAnalysis() {
    this.api.triggerAuctionsAnalysis().subscribe({
      next: (res: any) => {
        this.snackBar.open(`Triggered analysis for ${res.triggered_count} domains`, 'Close', { duration: 3000 });
      },
      error: (err: any) => {
        this.snackBar.open('Failed to trigger analysis', 'Close', { duration: 3000 });
      }
    });
  }

  triggerBulkRank() {
    this.api.triggerBulkRankAnalysis().subscribe({
      next: (res: any) => {
        this.snackBar.open(`Triggered bulk rank for ${res.triggered_count} domains`, 'Close', { duration: 3000 });
      },
      error: (err: any) => {
        this.snackBar.open('Failed to trigger bulk rank', 'Close', { duration: 3000 });
      }
    });
  }

  getStatusClass(status: string): string {
    switch(status) {
      case 'completed': return 'status-completed';
      case 'processing': 
      case 'parsing': return 'status-processing';
      case 'waiting_for_lock': return 'status-waiting';
      case 'failed': return 'status-failed';
      default: return 'status-pending';
    }
  }

  getStatusIcon(status: string) {
    switch(status) {
      case 'completed': return this.CheckCircle;
      case 'processing': 
      case 'parsing': return this.Activity;
      case 'waiting_for_lock': return this.Clock;
      case 'failed': return this.XCircle;
      default: return this.RefreshCcw;
    }
  }
}
