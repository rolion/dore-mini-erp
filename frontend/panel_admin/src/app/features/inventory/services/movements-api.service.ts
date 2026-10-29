import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import { toApiError } from '../models/api-error';
import {
  MovementListParams,
  StockMovement,
  StockMovementDetail,
  StockMovementDetailDto,
  StockMovementDto,
} from '../models/movement';

export function toMovement(dto: StockMovementDto): StockMovement {
  return {
    id: dto.id,
    occurredAt: dto.occurred_at,
    reference: dto.reference,
    product: dto.product,
    warehouse: dto.warehouse,
    kind: dto.kind,
    quantityIn: dto.quantity_in,
    quantityOut: dto.quantity_out,
    unitAbbreviation: dto.unit.abbreviation,
    status: dto.status,
    source: dto.source,
  };
}

export function toMovementDetail(dto: StockMovementDetailDto): StockMovementDetail {
  return {
    ...toMovement(dto),
    quantity: dto.quantity,
    reason: dto.reason,
    user: dto.user,
    reversedById: dto.reversed_by?.id ?? null,
    reversesId: dto.reverses?.id ?? null,
    createdAt: dto.created_at,
  };
}

/** Libro de movimientos: solo lectura (no hay alta, edición ni baja). */
@Injectable({
  providedIn: 'root',
})
export class MovementsApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/stock-movements/`;

  list(params: MovementListParams = {}): Observable<Page<StockMovement>> {
    let httpParams = new HttpParams();
    if (params.dateFrom) httpParams = httpParams.set('date_from', params.dateFrom);
    if (params.dateTo) httpParams = httpParams.set('date_to', params.dateTo);
    if (params.productId) httpParams = httpParams.set('product_id', params.productId);
    if (params.warehouseId) httpParams = httpParams.set('warehouse_id', params.warehouseId);
    if (params.kind) httpParams = httpParams.set('kind', params.kind);
    if (params.sourceType) httpParams = httpParams.set('source_type', params.sourceType);
    if (params.sourceType && params.sourceId) httpParams = httpParams.set('source_id', params.sourceId);
    if (params.page !== undefined) httpParams = httpParams.set('page', String(params.page));
    if (params.pageSize !== undefined) httpParams = httpParams.set('page_size', String(params.pageSize));
    return this.http.get<Page<StockMovementDto>>(this.baseUrl, { params: httpParams }).pipe(
      map((page): Page<StockMovement> => ({ ...page, results: page.results.map(toMovement) })),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }

  get(id: string): Observable<StockMovementDetail> {
    return this.http.get<StockMovementDetailDto>(`${this.baseUrl}${id}/`).pipe(
      map(toMovementDetail),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }
}
