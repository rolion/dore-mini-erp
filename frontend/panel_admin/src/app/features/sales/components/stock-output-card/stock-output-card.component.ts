import { DatePipe } from '@angular/common';
import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { StockOutput, formatQuantity } from '../../models/order';

/** Salida de inventario que generó la entrega del pedido, con acceso a sus movimientos. */
@Component({
  selector: 'app-stock-output-card',
  templateUrl: './stock-output-card.component.html',
  imports: [DatePipe, RouterLink],
})
export class StockOutputCardComponent {
  readonly orderId = input.required<string>();
  readonly output = input.required<StockOutput>();
  readonly format = formatQuantity;
}
