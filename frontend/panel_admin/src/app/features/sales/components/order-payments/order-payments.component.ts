import { Component, effect, input, output, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { inject } from '@angular/core';
import {
  FieldErrors,
  Order,
  PAYMENT_METHODS,
  PAYMENT_METHOD_LABELS,
  PaymentInput,
  PaymentMethod,
  todayIso,
} from '../../models/order';
import { MoneyPipe } from '../../pipes/money.pipe';

/**
 * Pagos del pedido y formulario de registro en la misma tarjeta, para ver el saldo mientras se escribe el
 * monto. El servidor valida (monto, saldo, fecha) y devuelve el pedido con los importes actualizados.
 */
@Component({
  selector: 'app-order-payments',
  templateUrl: './order-payments.component.html',
  imports: [ReactiveFormsModule, MoneyPipe],
})
export class OrderPaymentsComponent {
  readonly order = input.required<Order>();
  readonly busy = input(false);
  readonly errors = input<FieldErrors>({});
  readonly paymentSubmit = output<PaymentInput>();

  readonly methods = PAYMENT_METHODS;
  readonly methodLabels = PAYMENT_METHOD_LABELS;
  readonly formOpen = signal(false);
  readonly form = inject(FormBuilder).nonNullable.group({
    amount: ['', Validators.required],
    paymentMethod: ['CASH' as PaymentMethod, Validators.required],
    paymentDate: [todayIso(), Validators.required],
    reference: [''],
  });

  constructor() {
    // Un pago nuevo (o un pedido que ya no admite pagos) cierra y limpia el formulario.
    effect(() => {
      this.order().payments.length;
      this.close();
    });
    effect(() => {
      if (!this.order().canRegisterPayment) {
        this.formOpen.set(false);
      }
    });
  }

  open(): void {
    this.formOpen.set(true);
  }

  close(): void {
    this.formOpen.set(false);
    this.form.reset({ amount: '', paymentMethod: 'CASH', paymentDate: todayIso(), reference: '' });
  }

  submit(): void {
    if (this.form.invalid || this.busy()) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    this.paymentSubmit.emit({
      amount: value.amount.trim(),
      paymentMethod: value.paymentMethod,
      paymentDate: value.paymentDate,
      reference: value.reference.trim(),
    });
  }
}
