import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { CANCEL_REASON_MAX_LENGTH, Purchase } from '../../models/purchase';

/**
 * Cancelación de una compra: el motivo es obligatorio y el botón queda deshabilitado mientras esté vacío. Se cierra
 * devolviendo el motivo recortado (`dismiss` = volver sin cambios).
 */
@Component({
  selector: 'app-purchase-cancel-dialog',
  templateUrl: './purchase-cancel-dialog.component.html',
  imports: [ReactiveFormsModule],
})
export class PurchaseCancelDialogComponent {
  readonly maxLength = CANCEL_REASON_MAX_LENGTH;
  readonly form = inject(FormBuilder).nonNullable.group({ reason: '' });
  /** Compra a cancelar; la fija quien abre el diálogo. */
  purchase: Purchase | null = null;
  readonly activeModal = inject(NgbActiveModal);

  init(purchase: Purchase): void {
    this.purchase = purchase;
  }

  get reason(): string {
    return this.form.controls.reason.value.trim();
  }

  get canSubmit(): boolean {
    return this.reason.length > 0 && this.reason.length <= this.maxLength;
  }

  submit(): void {
    if (this.canSubmit) this.activeModal.close(this.reason);
  }
}
