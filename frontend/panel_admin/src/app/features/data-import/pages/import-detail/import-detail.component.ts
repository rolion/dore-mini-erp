import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { StatusBadgeComponent } from '../../../../shared/components/status-badge/status-badge.component';
import { ImportCountsComponent } from '../../components/import-counts/import-counts.component';
import { ImportRowsComponent } from '../../components/import-rows/import-rows.component';
import { ImportApiError, ImportRunDetail } from '../../models/sales-import';
import { SalesImportApiService } from '../../services/sales-import-api.service';
import { runStatusLabel, runStatusTone } from '../import-history/import-history.component';

/** Detalle de una importación: datos del archivo, contadores y detalle por venta con filtro por estado. */
@Component({
  selector: 'app-import-detail',
  templateUrl: './import-detail.component.html',
  imports: [TranslatePipe, RouterLink, DatePipe, StatusBadgeComponent, ImportCountsComponent, ImportRowsComponent],
})
export class ImportDetailComponent implements OnInit {
  private readonly api = inject(SalesImportApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);

  loading = true;
  errorMessage = '';
  run: ImportRunDetail | null = null;

  readonly tone = runStatusTone;
  readonly label = runStatusLabel;

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    this.loading = true;
    this.errorMessage = '';
    this.api
      .get(id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (run) => {
          this.run = run;
          this.loading = false;
        },
        error: (err: ImportApiError) => {
          this.errorMessage = err.message;
          this.loading = false;
        },
      });
  }
}
