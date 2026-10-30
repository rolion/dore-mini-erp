import { DatePipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { Purchase } from '../../models/purchase';

/**
 * Confirmación de una compra: resumen y aviso de que precios y cantidades quedarán bloqueados. Solo pregunta; quien
 * lo abre ejecuta la acción cuando se cierra con `true` (`dismiss` = volver sin cambios).
 */
@Component({
  selector: 'app-purchase-confirm-dialog',
  templateUrl: './purchase-confirm-dialog.component.html',
  imports: [DatePipe, MoneyPipe],
})
export class PurchaseConfirmDialogComponent {
  /** Compra a confirmar; la fija quien abre el diálogo. */
  purchase: Purchase | null = null;
  readonly activeModal = inject(NgbActiveModal);

  init(purchase: Purchase): void {
    this.purchase = purchase;
  }
}
