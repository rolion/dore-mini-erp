import { TranslatePipe } from '@ngx-translate/core';
import { DatePipe } from '@angular/common';
import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { finalize } from 'rxjs';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { Order, OrderApiError, OrderRuleError, ReturnPreview, formatQuantity } from '../../models/order';
import { OrdersApiService } from '../../services/orders-api.service';
import { reversalEventLabel } from '../order-reversal-card/order-reversal-card.component';

/** Motivo con el que se descarta el diálogo cuando el pedido cambió en el servidor y hay que recargarlo. */
export const STALE_ORDER_FOR_RETURN = 'stale';

/**
 * Confirmación de la devolución total de un pedido entregado: motivo, efecto en existencias y asientos, y el
 * reembolso externo si hay cobros. El efecto es informativo; el servidor vuelve a validar al confirmar. Se cierra
 * devolviendo el pedido devuelto.
 */
@Component({
  selector: 'app-return-dialog',
  templateUrl: './return-dialog.component.html',
  imports: [TranslatePipe, ReactiveFormsModule, MoneyPipe, DatePipe],
})
export class ReturnDialogComponent {
  readonly form = inject(FormBuilder).nonNullable.group({
    reason: ['', [Validators.required, Validators.maxLength(500)]],
    refundAcknowledged: [false],
  });
  readonly format = formatQuantity;
  readonly eventLabel = reversalEventLabel;

  order: Order | null = null;
  preview: ReturnPreview | null = null;
  saving = false;
  /** Mensaje del servidor de la última confirmación fallida (el diálogo conserva lo escrito). */
  errorMessage = '';

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(OrdersApiService);
  private destroyRef = inject(DestroyRef);

  init(order: Order, preview: ReturnPreview): void {
    this.order = order;
    this.preview = preview;
    if (preview.requiresRefundAcknowledgement) {
      this.form.controls.refundAcknowledged.addValidators(Validators.requiredTrue);
      this.form.controls.refundAcknowledged.updateValueAndValidity();
    }
  }

  get canConfirm(): boolean {
    return !this.saving && this.form.valid && !!this.form.controls.reason.value.trim();
  }

  confirm(): void {
    const order = this.order;
    if (!order || !this.canConfirm) return;
    const { reason, refundAcknowledged } = this.form.getRawValue();
    this.saving = true;
    this.errorMessage = '';
    this.api
      .returnOrder(order.id, reason.trim(), refundAcknowledged)
      .pipe(
        finalize(() => (this.saving = false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (returned) => this.activeModal.close(returned),
        error: (err: OrderApiError) => this.onError(err),
      });
  }

  private onError(err: OrderApiError): void {
    if (err instanceof OrderRuleError && err.code === 'invalid_transition') {
      // Otra pestaña o persona ya cambió el pedido: no se puede devolver desde esta foto.
      this.activeModal.dismiss(STALE_ORDER_FOR_RETURN);
      return;
    }
    this.errorMessage = err.fieldErrors.reason?.join(' ') ?? err.message;
  }
}
