import { DatePipe } from '@angular/common';
import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CustomerOrderSummary } from '../../models/customer';

/** Etiquetas de los códigos de Sales; un código desconocido se muestra tal cual en vez de romper la tabla. */
const STATUS_LABELS: Record<string, string> = {
  NEW: 'Nuevo',
  IN_PREPARATION: 'En preparación',
  READY: 'Listo',
  DELIVERED: 'Entregado',
  CANCELLED: 'Cancelado',
};

const PAYMENT_LABELS: Record<string, string> = {
  PENDING: 'Pendiente',
  PARTIAL: 'Parcial',
  PAID: 'Pagado',
  REFUNDED: 'Reembolsado',
};

/**
 * Historial de compras del cliente (REQ-CUS-004). Presenta los pedidos que recibe, sin hacer peticiones: los
 * carga la página del perfil desde Sales. Cada fila lleva al detalle del pedido.
 */
@Component({
  selector: 'app-customer-purchase-history',
  templateUrl: './customer-purchase-history.component.html',
  imports: [DatePipe, RouterLink],
})
export class CustomerPurchaseHistoryComponent {
  readonly orders = input<CustomerOrderSummary[]>([]);
  readonly loading = input(false);
  /** Mensaje de error si no se pudo cargar; el resto del perfil sigue visible. */
  readonly error = input('');
  /** Total de pedidos del cliente, por si el servidor devolvió solo los más recientes. */
  readonly total = input(0);

  statusLabel(code: string): string {
    return STATUS_LABELS[code] ?? code;
  }

  paymentLabel(code: string): string {
    return PAYMENT_LABELS[code] ?? code;
  }
}
