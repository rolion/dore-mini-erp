import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import { CustomerOrderSummary } from '../models/customer';

export const HISTORY_ERROR_MESSAGE = 'No se pudo cargar el historial de compras.';
export const HISTORY_PAGE_SIZE = 100;

interface OrderRowDto {
  id: string;
  order_date: string;
  total: string;
  status: string;
  payment_status: string;
}

export interface CustomerOrderHistory {
  orders: CustomerOrderSummary[];
  /** Total de pedidos del cliente; puede ser mayor que `orders` si superan el tamaño de página. */
  total: number;
}

/**
 * Historial de compras del cliente. Consume el contrato HTTP de pedidos (ADR historial-compras): Customers no
 * importa nada de Sales, solo conoce esta forma de respuesta.
 */
@Injectable({
  providedIn: 'root',
})
export class CustomerOrdersApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/orders/`;

  /** Los pedidos más recientes primero; funciona igual para clientes inactivos. */
  list(customerId: string): Observable<CustomerOrderHistory> {
    const params = new HttpParams().set('customer_id', customerId).set('page_size', String(HISTORY_PAGE_SIZE));
    return this.http.get<Page<OrderRowDto>>(this.baseUrl, { params }).pipe(
      map((page) => ({
        total: page.count,
        orders: page.results.map(
          (row): CustomerOrderSummary => ({
            id: row.id,
            date: row.order_date,
            total: row.total,
            status: row.status,
            paymentStatus: row.payment_status,
          }),
        ),
      })),
      catchError((err: HttpErrorResponse) => throwError(() => new Error(HISTORY_ERROR_MESSAGE, { cause: err }))),
    );
  }
}
