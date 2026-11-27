import { TranslatePipe } from '@ngx-translate/core';
import { DatePipe } from '@angular/common';
import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { tr } from '../../../../core/i18n/translate';
import { Order, formatQuantity } from '../../models/order';

/** Nombre legible del evento contable del pedido (el código llega del servidor). */
export function reversalEventLabel(event: string): string {
  switch (event) {
    case 'SALE_DELIVERY':
      return tr('SALES.ORDER_RETURN.EVENT_SALE_DELIVERY');
    case 'SALE_RECOGNITION':
      return tr('SALES.ORDER_RETURN.EVENT_SALE_RECOGNITION');
    case 'INVENTORY_SALE_COST':
      return tr('SALES.ORDER_RETURN.EVENT_INVENTORY_SALE_COST');
    case 'SALE_ADVANCE':
      return tr('SALES.ORDER_RETURN.EVENT_SALE_ADVANCE');
    case 'SALE_PAYMENT':
      return tr('SALES.ORDER_RETURN.EVENT_SALE_PAYMENT');
    default:
      return event;
  }
}

/**
 * Historial de una cancelación o devolución: fecha, usuario, motivo, reembolso y los movimientos y asientos
 * vinculados (originales y reversos). La venta original se conserva.
 */
@Component({
  selector: 'app-order-reversal-card',
  templateUrl: './order-reversal-card.component.html',
  imports: [TranslatePipe, DatePipe, RouterLink, MoneyPipe],
})
export class OrderReversalCardComponent {
  readonly order = input.required<Order>();
  readonly format = formatQuantity;
  readonly eventLabel = reversalEventLabel;

  get returned(): boolean {
    return this.order().status === 'RETURNED';
  }

  get at(): string | null {
    return this.returned ? this.order().returnedAt : this.order().cancelledAt;
  }

  get by(): string {
    return this.returned ? this.order().returnedByName : this.order().cancelledByName;
  }

  get reason(): string {
    return this.returned ? this.order().returnReason : this.order().cancellationReason;
  }
}
