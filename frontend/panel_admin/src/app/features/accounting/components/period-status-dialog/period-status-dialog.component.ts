import { Component, inject } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { FiscalPeriod } from '../../models/fiscal-period';

export type PeriodAction = 'close' | 'reopen';

/** Confirma cerrar o reabrir un período; informa del efecto antes de hacerlo. */
@Component({
  selector: 'app-period-status-dialog',
  templateUrl: './period-status-dialog.component.html',
  imports: [TranslatePipe],
})
export class PeriodStatusDialogComponent {
  period!: FiscalPeriod;
  action: PeriodAction = 'close';

  readonly activeModal = inject(NgbActiveModal);

  get isClose(): boolean {
    return this.action === 'close';
  }
}
