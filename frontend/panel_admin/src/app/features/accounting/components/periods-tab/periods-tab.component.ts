import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { ToastrService } from 'ngx-toastr';
import { EMPTY, Subject, catchError, finalize, switchMap } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { AccountingApiError } from '../../models/accounting';
import { FiscalPeriod } from '../../models/fiscal-period';
import { FiscalPeriodsApiService } from '../../services/fiscal-periods-api.service';
import { PeriodAction, PeriodStatusDialogComponent } from '../period-status-dialog/period-status-dialog.component';
import { PeriodDialogComponent } from '../period-dialog/period-dialog.component';

/** Pestaña «Períodos fiscales»: listado (más reciente primero), alta/edición, cierre y reapertura. */
@Component({
  selector: 'app-periods-tab',
  templateUrl: './periods-tab.component.html',
  styleUrl: '../accounts-tab/accounts-tab.component.scss',
  imports: [TranslatePipe, DatePipe],
})
export class PeriodsTabComponent implements OnInit {
  rows: FiscalPeriod[] = [];
  loading = false;
  errorMessage = '';
  /** Motivo de un conflicto del servidor al cerrar o reabrir, visible sobre la tabla. */
  blockReason = '';

  private api = inject(FiscalPeriodsApiService);
  private modal = inject(NgbModal);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  ngOnInit(): void {
    this.reload$
      .pipe(
        switchMap(() => {
          this.loading = true;
          this.errorMessage = '';
          return this.api.list().pipe(
            catchError((err: AccountingApiError) => {
              this.errorMessage = err.message;
              this.rows = [];
              return EMPTY;
            }),
            finalize(() => (this.loading = false)),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((periods) => (this.rows = periods));
    this.reload$.next();
  }

  reload(): void {
    this.reload$.next();
  }

  openDialog(period?: FiscalPeriod): void {
    this.blockReason = '';
    const ref = this.modal.open(PeriodDialogComponent, { centered: true, backdrop: 'static' });
    if (period) {
      (ref.componentInstance as PeriodDialogComponent).edit(period);
    }
    ref.result.then(
      () => this.reload$.next(),
      () => undefined, // cancelado
    );
  }

  /** Cerrar y reabrir piden confirmación y explican el efecto. */
  confirm(period: FiscalPeriod, action: PeriodAction): void {
    this.blockReason = '';
    const ref = this.modal.open(PeriodStatusDialogComponent, { centered: true, backdrop: 'static' });
    const dialog = ref.componentInstance as PeriodStatusDialogComponent;
    dialog.period = period;
    dialog.action = action;
    ref.result.then(
      () => this.apply(period, action),
      () => undefined, // cancelado
    );
  }

  private apply(period: FiscalPeriod, action: PeriodAction): void {
    const request = action === 'close' ? this.api.close(period.id) : this.api.reopen(period.id);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.toastr.success(action === 'close' ? tr('ACCOUNTING.FISCAL_PERIODS.CERRADO_OK') : tr('ACCOUNTING.FISCAL_PERIODS.REABIERTO_OK'));
        this.reload$.next();
      },
      error: (err: AccountingApiError) => {
        if (err.status === 409) {
          this.blockReason = err.message;
          this.reload$.next();
        } else {
          this.toastr.error(err.message);
        }
      },
    });
  }
}
