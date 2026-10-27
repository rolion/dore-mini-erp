import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, of } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { PAYMENT_METHODS, PaymentMethod, SALES_CHANNELS, SalesChannel } from '../models/order';

/** Valores sugeridos por la configuración de Ventas de la empresa (vacío = sin predeterminado). */
export interface SalesDefaults {
  salesChannel: SalesChannel | '';
  paymentMethod: PaymentMethod | '';
}

export const NO_SALES_DEFAULTS: SalesDefaults = { salesChannel: '', paymentMethod: '' };

interface SettingsDto {
  settings: { key: string; value: string }[];
}

/**
 * Predeterminados de canal y método de pago: solo precargan los formularios (el usuario puede cambiarlos). Si la
 * configuración no se puede leer, los formularios quedan como siempre.
 */
@Injectable({
  providedIn: 'root',
})
export class SalesSettingsService {
  private http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/settings/sales/`;

  defaults(): Observable<SalesDefaults> {
    return this.http.get<SettingsDto>(this.url).pipe(
      map((dto): SalesDefaults => {
        const value = (key: string): string => dto.settings.find((s) => s.key === key)?.value ?? '';
        const channel = value('sales.default_sales_channel');
        const method = value('sales.default_payment_method');
        return {
          salesChannel: SALES_CHANNELS.find((c) => c === channel) ?? '',
          paymentMethod: PAYMENT_METHODS.find((m) => m === method) ?? '',
        };
      }),
      catchError(() => of(NO_SALES_DEFAULTS)),
    );
  }
}
