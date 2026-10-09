import { Component, computed, input } from '@angular/core';
import { PAYMENT_STATUS_COLORS, PAYMENT_STATUS_LABELS, PaymentStatus } from '../../models/order';

/** Estado de pago del pedido: texto + icono de monedas + color (el color nunca va solo). */
@Component({
  selector: 'app-payment-status-badge',
  template: `<div [class]="color()">
    <i class="fas fa-coins me-1" aria-hidden="true"></i>{{ label() }}
  </div>`,
})
export class PaymentStatusBadgeComponent {
  readonly status = input.required<PaymentStatus>();
  readonly label = computed(() => PAYMENT_STATUS_LABELS[this.status()]);
  readonly color = computed(() => `badge-outline d-inline-block ${PAYMENT_STATUS_COLORS[this.status()]}`);
}
