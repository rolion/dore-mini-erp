import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { tr } from '../../../core/i18n/translate';
import { CrmCustomer, CrmCustomerDto, CrmCustomerPage, CrmCustomerPageDto, CrmListParams } from '../models/crm-customer';

export class CrmApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export function toCrmCustomer(dto: CrmCustomerDto): CrmCustomer {
  return {
    id: dto.customer_id,
    name: dto.display_name,
    phone: dto.phone,
    lastPurchaseAt: dto.last_purchase_at,
    orderCount: dto.order_count,
    outstandingAmount: dto.outstanding_amount,
    currency: dto.currency,
  };
}

@Injectable({ providedIn: 'root' })
export class CrmCustomersApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/crm/customers/`;

  list(params: CrmListParams = {}): Observable<CrmCustomerPage> {
    let httpParams = new HttpParams();
    if (params.search) httpParams = httpParams.set('search', params.search);
    if (params.warehouseId) httpParams = httpParams.set('warehouse_id', params.warehouseId);
    if (params.page !== undefined) httpParams = httpParams.set('page', String(params.page));
    if (params.pageSize !== undefined) httpParams = httpParams.set('page_size', String(params.pageSize));
    return this.http.get<CrmCustomerPageDto>(this.baseUrl, { params: httpParams }).pipe(
      map((page): CrmCustomerPage => ({ count: page.count, results: page.results.map(toCrmCustomer), meta: page.meta })),
      catchError((err: HttpErrorResponse) => throwError(() => new CrmApiError(tr('CRM.CUSTOMER_LIST.ERROR'), err.status))),
    );
  }
}
