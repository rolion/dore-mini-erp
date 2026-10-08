import { Injectable, inject } from '@angular/core';
import { Observable, catchError, defer, map, of } from 'rxjs';
import { CustomersApiService } from '../../customers';
import { OrderCustomer } from '../models/order';

export const CUSTOMER_SEARCH_PAGE_SIZE = 20;

/** Búsqueda de clientes activos (por nombre o teléfono) para los selectores del formulario y de la lista. */
@Injectable({
  providedIn: 'root',
})
export class CustomerOptionsService {
  private customersApi = inject(CustomersApiService);

  /**
   * `ng-select` emite `null` por el typeahead al elegir o limpiar una opción, así que el término puede faltar.
   * Cualquier fallo (de red, o al construir la petición) deja la lista vacía en vez de terminar el stream del selector.
   */
  search(term: string | null | undefined): Observable<OrderCustomer[]> {
    return defer(() =>
      this.customersApi.list({ search: (term ?? '').trim(), active: true, pageSize: CUSTOMER_SEARCH_PAGE_SIZE }),
    ).pipe(
      map((page) => page.results.map((customer) => ({ id: customer.id, name: customer.name }))),
      catchError(() => of([] as OrderCustomer[])),
    );
  }
}
