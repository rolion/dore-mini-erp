import { TranslatePipe } from '@ngx-translate/core';
import { DatePipe } from '@angular/common';
import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { ORDER_STATUSES, OrderStatus, PAYMENT_STATUSES, PaymentStatus } from '../../../sales/models/order';
import { OrderStatusBadgeComponent } from '../../../sales/components/order-status-badge/order-status-badge.component';
import { PaymentStatusBadgeComponent } from '../../../sales/components/payment-status-badge/payment-status-badge.component';
import { CustomerOrderSummary } from '../../models/customer';
import { CANCELLED_STATUS } from '../../models/customer-purchase-summary';

/**
 * Historial de compras del cliente (REQ-CUS-004). Presenta los pedidos que recibe, sin hacer peticiones: los
 * carga la página del perfil desde Sales. Cada fila lleva al detalle del pedido.
 */
@Component({
  selector: 'app-customer-purchase-history',
  templateUrl: './customer-purchase-history.component.html',
  styleUrl: './customer-purchase-history.component.scss',
  imports: [TranslatePipe, DatePipe, RouterLink, MoneyPipe, OrderStatusBadgeComponent, PaymentStatusBadgeComponent],
})
export class CustomerPurchaseHistoryComponent {
  readonly orders = input<CustomerOrderSummary[]>([]);
  readonly loading = input(false);
  /** Mensaje de error si no se pudo cargar; el resto del perfil sigue visible. */
  readonly error = input('');
  /** Total de pedidos del cliente, por si el servidor devolvió solo los más recientes. */
  readonly total = input(0);
  readonly customerId = input('');
  readonly customerName = input('');
  /** El módulo Pedidos está disponible: se ofrecen los enlaces a la lista de pedidos. */
  readonly ordersEnabled = input(true);
  /** Se puede crear un pedido para este cliente (activo y módulo Pedidos habilitado). */
  readonly canCreateOrder = input(false);

  isCancelled(order: CustomerOrderSummary): boolean {
    return order.status === CANCELLED_STATUS;
  }

  /** Un código desconocido devuelve `null` y la plantilla lo muestra como texto, sin romper la tabla (EDGE-05). */
  orderStatus(code: string): OrderStatus | null {
    return ORDER_STATUSES.find((status) => status === code) ?? null;
  }

  paymentStatus(code: string): PaymentStatus | null {
    return PAYMENT_STATUSES.find((status) => status === code) ?? null;
  }
}
