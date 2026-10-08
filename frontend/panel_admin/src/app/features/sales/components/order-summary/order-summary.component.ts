import { Component, effect, input, output } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { FieldErrors, Order } from '../../models/order';
import { MoneyPipe } from '../../pipes/money.pipe';

/**
 * Importes del pedido. Todo se muestra tal como lo calcula el servidor; el total nunca es un campo editable
 * (REQ-SAL-005). Solo el descuento se puede cambiar, mientras el pedido sea editable.
 */
@Component({
  selector: 'app-order-summary',
  templateUrl: './order-summary.component.html',
  imports: [ReactiveFormsModule, MoneyPipe],
})
export class OrderSummaryComponent {
  readonly order = input.required<Order>();
  readonly busy = input(false);
  readonly errors = input<FieldErrors>({});
  readonly discountSubmit = output<string>();

  readonly discountControl = new FormControl('', { nonNullable: true });

  constructor() {
    // El campo refleja siempre el descuento vigente del servidor.
    effect(() => this.discountControl.setValue(this.order().discount, { emitEvent: false }));
  }

  submitDiscount(): void {
    const value = this.discountControl.value.trim();
    if (!this.busy() && value) {
      this.discountSubmit.emit(value);
    }
  }
}
