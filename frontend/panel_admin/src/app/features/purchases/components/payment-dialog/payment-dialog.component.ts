import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { finalize } from 'rxjs';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import {
  PAYMENT_METHODS,
  PAYMENT_METHOD_LABELS,
  Payment,
  PaymentApiError,
  PaymentFieldErrors,
  PaymentMethod,
} from '../../models/payment';
import { Purchase, todayIso } from '../../models/purchase';
import { amountError } from '../../services/payment-amounts';
import { PaymentsApiService } from '../../services/payments-api.service';

/**
 * Alta de un pago. El diálogo hace la llamada: si el servidor rechaza, se queda abierto con lo escrito y muestra el
 * error. `paymentId` se genera al abrir y se reutiliza en cada reintento (idempotencia). Se cierra devolviendo el pago.
 */
@Component({
  selector: 'app-payment-dialog',
  templateUrl: './payment-dialog.component.html',
  imports: [ReactiveFormsModule, MoneyPipe],
})
export class PaymentDialogComponent {
  readonly methods = PAYMENT_METHODS;
  readonly methodLabels = PAYMENT_METHOD_LABELS;
  readonly today = todayIso();
  readonly form = inject(FormBuilder).nonNullable.group({
    paymentDate: [todayIso(), Validators.required],
    amount: '',
    paymentMethod: '' as PaymentMethod | '',
  });
  readonly activeModal = inject(NgbActiveModal);
  /** Compra a pagar; la fija quien abre el diálogo. */
  purchase: Purchase | null = null;
  submitting = false;
  /** Se muestra tras un intento fallido o tocado el campo. */
  touched = false;
  serverErrors: PaymentFieldErrors = {};
  generalError = '';

  private paymentId: string = crypto.randomUUID();
  private api = inject(PaymentsApiService);
  private destroyRef = inject(DestroyRef);

  init(purchase: Purchase): void {
    this.purchase = purchase;
  }

  get balance(): string {
    return this.purchase?.balance ?? '0.00';
  }

  get amountMessage(): string | null {
    return amountError(this.form.controls.amount.value, this.balance);
  }

  get dateMessage(): string | null {
    const date = this.form.controls.paymentDate.value;
    if (!date) return 'La fecha es obligatoria.';
    return date > this.today ? 'La fecha no puede ser futura.' : null;
  }

  get methodMessage(): string | null {
    return this.form.controls.paymentMethod.value ? null : 'Elige un método de pago.';
  }

  get canSubmit(): boolean {
    return !this.submitting && !this.amountMessage && !this.dateMessage && !this.methodMessage;
  }

  /** Rellena el monto con todo el saldo. */
  payInFull(): void {
    this.form.controls.amount.setValue(this.balance);
    this.touched = true;
  }

  submit(): void {
    this.touched = true;
    const method = this.form.controls.paymentMethod.value;
    if (!this.purchase || !this.canSubmit || !method) return;
    this.submitting = true;
    this.serverErrors = {};
    this.generalError = '';
    this.api
      .create(this.purchase.id, {
        paymentId: this.paymentId,
        amount: this.form.controls.amount.value.trim(),
        paymentMethod: method,
        paymentDate: this.form.controls.paymentDate.value,
      })
      .pipe(
        finalize(() => (this.submitting = false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (payment: Payment) => this.activeModal.close(payment),
        error: (err: PaymentApiError) => {
          this.serverErrors = err.fieldErrors;
          const hasField = !!(err.fieldErrors.amount || err.fieldErrors.paymentMethod || err.fieldErrors.paymentDate);
          this.generalError = hasField ? '' : err.message;
        },
      });
  }
}
