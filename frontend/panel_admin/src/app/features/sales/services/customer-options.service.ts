import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, of } from 'rxjs';
import { CustomersApiService } from '../../customers';
import { OrderCustomer } from '../models/order';

export const CUSTOMER_SEARCH_PAGE_SIZE = 20;

/** Búsqueda de clientes activos (por nombre o teléfono) para los selectores del formulario y de la lista. */
@Injectable({
  providedIn: 'root',
})
export class CustomerOptionsService {
  private customersApi = inject(CustomersApiService);

  /** Un fallo de red deja la lista vacía en vez de romper el selector. */
  search(term: string): Observable<OrderCustomer[]> {
    return this.customersApi.list({ search: term.trim(), active: true, pageSize: CUSTOMER_SEARCH_PAGE_SIZE }).pipe(
      map((page) => page.results.map((customer) => ({ id: customer.id, name: customer.name }))),
      catchError(() => of([] as OrderCustomer[])),
    );
  }
}
