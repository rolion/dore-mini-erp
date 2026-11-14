import { Component, inject } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';

/** Confirma la aplicación: cuántas entradas y qué importe se crearán, y lo que NO hace. */
@Component({
  selector: 'app-regularization-confirm-dialog',
  templateUrl: './regularization-confirm-dialog.component.html',
  imports: [TranslatePipe],
})
export class RegularizationConfirmDialogComponent {
  count = 0;
  /** Importes ya formateados por moneda (p. ej. «Bs 150.00»). */
  amounts = '';

  readonly activeModal = inject(NgbActiveModal);
}
