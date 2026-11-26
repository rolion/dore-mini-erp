import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { catchError, finalize, of } from 'rxjs';
import { ModulesService } from '../../../../core/service/modules.service';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { FiscalPeriod } from '../../../accounting/models/fiscal-period';
import { FiscalPeriodsApiService } from '../../../accounting/services/fiscal-periods-api.service';
import { PaidReportFilters, PaidReportFormat, PaidReportPage } from '../../models/paid-report';
import { PaidReportApiService } from '../../services/paid-report-api.service';

export const PAGE_SIZE = 10;

/** «Ingresos por venta»: pedidos entregados y pagados, con filtros de fecha y período fiscal y exportación. */
@Component({
  selector: 'app-paid-report',
  templateUrl: './paid-report.component.html',
  imports: [TranslatePipe, RouterLink, ReactiveFormsModule, NgbPagination, MoneyPipe],
})
export class PaidReportComponent implements OnInit {
  readonly pageSize = PAGE_SIZE;
  readonly filterForm = inject(FormBuilder).nonNullable.group({ dateFrom: [''], dateTo: [''], fiscalPeriodId: [''] });

  report: PaidReportPage | null = null;
  page = 1;
  loading = false;
  errorMessage = '';
  exportError = '';
  exporting: PaidReportFormat | null = null;
  rangeInvalid = false;
  periods: FiscalPeriod[] = [];

  private api = inject(PaidReportApiService);
  private periodsApi = inject(FiscalPeriodsApiService);
  private modules = inject(ModulesService);
  private destroyRef = inject(DestroyRef);

  get filters(): PaidReportFilters {
    return this.filterForm.getRawValue();
  }

  get hasFilters(): boolean {
    const { dateFrom, dateTo, fiscalPeriodId } = this.filters;
    return Boolean(dateFrom || dateTo || fiscalPeriodId);
  }

  get from(): number {
    return (this.page - 1) * PAGE_SIZE + 1;
  }

  get to(): number {
    return Math.min(this.page * PAGE_SIZE, this.report?.count ?? 0);
  }

  ngOnInit(): void {
    if (!this.modules.isDisabled('accounting')) {
      this.periodsApi
        .list()
        .pipe(catchError(() => of([] as FiscalPeriod[])), takeUntilDestroyed(this.destroyRef))
        .subscribe((periods) => (this.periods = periods));
    }
    this.load();
  }

  applyFilters(): void {
    this.page = 1;
    this.load();
  }

  clearFilters(): void {
    this.filterForm.reset();
    this.applyFilters();
  }

  changePage(page: number): void {
    this.page = page;
    this.load();
  }

  load(): void {
    const { dateFrom, dateTo } = this.filters;
    this.rangeInvalid = Boolean(dateFrom && dateTo && dateFrom > dateTo);
    if (this.rangeInvalid) return;
    this.loading = true;
    this.errorMessage = '';
    this.api
      .list(this.filters, this.page, PAGE_SIZE)
      .pipe(
        finalize(() => (this.loading = false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (report) => (this.report = report),
        error: (err: Error) => {
          this.report = null;
          this.errorMessage = err.message;
        },
      });
  }

  export(format: PaidReportFormat): void {
    if (this.exporting || this.rangeInvalid) return;
    this.exporting = format;
    this.exportError = '';
    this.api
      .export(format, this.filters)
      .pipe(
        finalize(() => (this.exporting = null)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (blob) => this.download(blob, `ingresos-por-venta.${format}`),
        error: (err: Error) => (this.exportError = err.message),
      });
  }

  private download(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }
}
