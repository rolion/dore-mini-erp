import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { Subscription } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { StatusBadgeComponent, StatusTone } from '../../../../shared/components/status-badge/status-badge.component';
import { ImportApiError, ImportRunStatus, ImportRunSummary } from '../../models/sales-import';
import { SalesImportApiService } from '../../services/sales-import-api.service';

/** Tono y texto del estado de una importación (compartido con el detalle). */
export function runStatusTone(status: ImportRunStatus): StatusTone {
  return status === 'COMPLETED' ? 'success' : status === 'FAILED' ? 'danger' : 'info';
}

export function runStatusLabel(status: ImportRunStatus): string {
  switch (status) {
    case 'COMPLETED':
      return tr('DATA_IMPORT.RUN_STATUS.COMPLETED');
    case 'FAILED':
      return tr('DATA_IMPORT.RUN_STATUS.FAILED');
    case 'QUEUED':
      return tr('DATA_IMPORT.RUN_STATUS.QUEUED');
    default:
      return tr('DATA_IMPORT.RUN_STATUS.RUNNING');
  }
}

/** Historial de importaciones de ventas: lista de solo lectura con paginación. */
@Component({
  selector: 'app-import-history',
  templateUrl: './import-history.component.html',
  imports: [TranslatePipe, RouterLink, DatePipe, NgbPagination, StatusBadgeComponent],
})
export class ImportHistoryComponent implements OnInit {
  private readonly api = inject(SalesImportApiService);
  private readonly destroyRef = inject(DestroyRef);
  private request: Subscription | null = null;

  loading = true;
  errorMessage = '';
  runs: ImportRunSummary[] = [];
  total = 0;
  page = 1;
  pageSize = 10;

  readonly tone = runStatusTone;
  readonly label = runStatusLabel;

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.request?.unsubscribe();
    this.loading = true;
    this.errorMessage = '';
    this.request = this.api
      .list(this.page)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (page) => {
          this.runs = page.results;
          this.total = page.count;
          if (page.next && page.results.length > 0) {
            this.pageSize = page.results.length;
          }
          this.loading = false;
        },
        error: (err: ImportApiError) => {
          this.errorMessage = err.message;
          this.loading = false;
        },
      });
  }

  onPage(page: number): void {
    this.page = page;
    this.load();
  }
}
