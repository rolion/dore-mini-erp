import { Component, DestroyRef, OnInit, inject, input } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { Subscription } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { StatusBadgeComponent, StatusTone } from '../../../../shared/components/status-badge/status-badge.component';
import { IMPORT_ROW_STATUSES, ImportApiError, ImportRow, ImportRowStatus } from '../../models/sales-import';
import { SalesImportApiService } from '../../services/sales-import-api.service';

const TONES: Record<ImportRowStatus, StatusTone> = {
  CREATED: 'success',
  SKIPPED_DUPLICATE: 'muted',
  CREATED_WITHOUT_POSTING: 'warning',
  FAILED: 'danger',
};

/** Detalle por venta de una importación (paso 4 y detalle del historial): filtro por estado y paginación. */
@Component({
  selector: 'app-import-rows',
  templateUrl: './import-rows.component.html',
  imports: [TranslatePipe, RouterLink, NgbPagination, StatusBadgeComponent],
})
export class ImportRowsComponent implements OnInit {
  readonly runId = input.required<string>();

  readonly statuses = IMPORT_ROW_STATUSES;
  private readonly api = inject(SalesImportApiService);
  private readonly destroyRef = inject(DestroyRef);
  private request: Subscription | null = null;

  loading = true;
  errorMessage = '';
  rows: ImportRow[] = [];
  total = 0;
  page = 1;
  pageSize = 10;
  status: ImportRowStatus | '' = '';

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.request?.unsubscribe();
    this.loading = true;
    this.errorMessage = '';
    this.request = this.api
      .rows(this.runId(), this.status, this.page)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (page) => {
          this.rows = page.results;
          this.total = page.count;
          // El tamaño de página lo define el servidor: se infiere de la primera página llena.
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

  onStatusChange(event: Event): void {
    this.status = (event.target as HTMLSelectElement).value as ImportRowStatus | '';
    this.page = 1;
    this.load();
  }

  onPage(page: number): void {
    this.page = page;
    this.load();
  }

  tone(status: ImportRowStatus): StatusTone {
    return TONES[status];
  }

  label(status: ImportRowStatus): string {
    switch (status) {
      case 'CREATED':
        return tr('DATA_IMPORT.ROW_STATUS.CREATED');
      case 'SKIPPED_DUPLICATE':
        return tr('DATA_IMPORT.ROW_STATUS.SKIPPED_DUPLICATE');
      case 'CREATED_WITHOUT_POSTING':
        return tr('DATA_IMPORT.ROW_STATUS.CREATED_WITHOUT_POSTING');
      default:
        return tr('DATA_IMPORT.ROW_STATUS.FAILED');
    }
  }
}
