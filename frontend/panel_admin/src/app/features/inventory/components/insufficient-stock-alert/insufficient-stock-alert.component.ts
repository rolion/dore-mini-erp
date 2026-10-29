import { Component, input } from '@angular/core';
import { InsufficientStockInfo } from '../../models/api-error';

/** Aviso de una salida rechazada por saldo insuficiente: producto, almacén, cantidad solicitada y existencia actual. */
@Component({
  selector: 'app-insufficient-stock-alert',
  templateUrl: './insufficient-stock-alert.component.html',
})
export class InsufficientStockAlertComponent {
  readonly info = input.required<InsufficientStockInfo>();
}
