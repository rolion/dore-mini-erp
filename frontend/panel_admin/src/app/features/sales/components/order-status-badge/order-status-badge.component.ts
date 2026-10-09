import { Component, computed, input } from '@angular/core';
import { ORDER_STATUS_COLORS, ORDER_STATUS_LABELS, OrderStatus } from '../../models/order';

/** Estado de entrega del pedido: texto + icono de camión + color (el color nunca va solo). */
@Component({
  selector: 'app-order-status-badge',
  template: `<div class="badge-outline d-inline-block" [class]="color()">
    <i class="fas fa-truck me-1" aria-hidden="true"></i>{{ label() }}
  </div>`,
})
export class OrderStatusBadgeComponent {
  readonly status = input.required<OrderStatus>();
  readonly label = computed(() => ORDER_STATUS_LABELS[this.status()]);
  readonly color = computed(() => `badge-outline d-inline-block ${ORDER_STATUS_COLORS[this.status()]}`);
}
