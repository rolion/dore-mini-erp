import { DatePipe } from '@angular/common';
import { Component, input } from '@angular/core';
import { CustomerOrderSummary } from '../../models/customer';

/**
 * Historial de compras del cliente (REQ-CUS-004). Solo presenta los pedidos que recibe: el origen
 * lo proveerá Sales (ADR historial-compras), por eso aquí no hay ninguna petición de red.
 */
@Component({
  selector: 'app-customer-purchase-history',
  templateUrl: './customer-purchase-history.component.html',
  imports: [DatePipe],
})
export class CustomerPurchaseHistoryComponent {
  readonly orders = input<CustomerOrderSummary[]>([]);
}
