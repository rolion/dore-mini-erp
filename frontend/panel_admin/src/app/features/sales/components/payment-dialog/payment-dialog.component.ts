import { TranslatePipe } from '@ngx-translate/core';
import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { finalize } from 'rxjs';
import { PostingIssuesAlertComponent } from '../../../../shared/components/posting-issues-alert/posting-issues-alert.component';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import {
  FieldErrors,
  Order,
  OrderApiError,
  OrderRuleError,
  PAYMENT_METHODS,
  PAYMENT_METHOD_LABELS,
  PaymentMethod,
  PostingIssue,
  todayIso,
} from '../../models/order';
import { OrdersApiService } from '../../services/orders-api.service';
import { SalesSettingsService } from '../../services/sales-settings.service';

/** Motivo con el que se descarta el modal cuando el pedido cambió en el servidor y hay que recargarlo. */
export const STALE_ORDER_FOR_PAYMENT = 'stale';

/**
 * Registro de un pago en un modal. El servidor valida (monto, saldo, fecha, estado) y devuelve el pedido con los
 * importes actualizados; el modal se cierra devolviéndolo. Los errores se muestran aquí sin perder lo escrito, y el
 * mismo intento (clave de idempotencia) se reutiliza en los reintentos.
 */
@Component({
  selector: 'app-payment-dialog',
  templateUrl: './payment-dialog.component.html',
  imports: [TranslatePipe, ReactiveFormsModule, MoneyPipe, PostingIssuesAlertComponent],
})
export class PaymentDialogComponent {
  readonly methods = PAYMENT_METHODS;
  readonly methodLabels = PAYMENT_METHOD_LABELS;
  readonly today = todayIso();
  readonly form = inject(FormBuilder).nonNullable.group({
    amount: ['', Validators.required],
    paymentMethod: ['CASH' as PaymentMethod, Validators.required],
    paymentDate: [todayIso(), Validators.required],
    reference: [''],
  });

  /** Pedido al que se cobra; lo fija quien abre el modal. */
  order: Order | null = null;
  saving = false;
  errors: FieldErrors = {};
  errorMessage = '';
  postingIssues: PostingIssue[] = [];

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(OrdersApiService);
  private destroyRef = inject(DestroyRef);
  /** Igual en cada reintento; cambia si la persona modifica lo escrito. */
  private attemptKey: string = crypto.randomUUID();

  constructor() {
    this.form.valueChanges.pipe(takeUntilDestroyed()).subscribe(() => (this.attemptKey = crypto.randomUUID()));
    inject(SalesSettingsService)
      .defaults()
      .pipe(takeUntilDestroyed())
      .subscribe((defaults) => {
        if (defaults.paymentMethod && this.form.controls.paymentMethod.pristine) {
          this.form.controls.paymentMethod.setValue(defaults.paymentMethod, { emitEvent: false });
        }
      });
  }

  init(order: Order): void {
    this.order = order;
  }

  submit(): void {
    const order = this.order;
    if (!order || this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    this.saving = true;
    this.errors = {};
    this.errorMessage = '';
    this.postingIssues = [];
    this.api
      .registerPayment(order.id, {
        amount: value.amount.trim(),
        paymentMethod: value.paymentMethod,
        paymentDate: value.paymentDate,
        reference: value.reference.trim(),
        idempotencyKey: this.attemptKey,
      })
      .pipe(
        finalize(() => (this.saving = false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (updated) => this.activeModal.close(updated),
        error: (err: OrderApiError) => this.onError(err),
      });
  }

  private onError(err: OrderApiError): void {
    if (err.status === 400 && Object.keys(err.fieldErrors).length) {
      this.errors = err.fieldErrors;
      return;
    }
    if (err instanceof OrderRuleError && err.postingIssues.length) {
      this.postingIssues = err.postingIssues;
      return;
    }
    if (err instanceof OrderRuleError && (err.code === 'invalid_transition' || err.code === 'order_cancelled')) {
      this.activeModal.dismiss(STALE_ORDER_FOR_PAYMENT);
      return;
    }
    this.errorMessage = err.message;
  }
}
