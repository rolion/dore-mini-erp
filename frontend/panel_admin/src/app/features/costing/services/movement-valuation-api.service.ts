import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import {
  CostingApiError,
  MovementValuation,
  MovementValuationDto,
  MovementValuationParams,
} from '../models/movement-valuation';

const GENERIC_MESSAGE = 'Ocurrió un error inesperado. Inténtalo de nuevo.';
const NETWORK_MESSAGE = 'No se pudo conectar con el servidor. Inténtalo de nuevo.';

function toError(err: HttpErrorResponse): CostingApiError {
  if (err.status === 0) {
    return new CostingApiError(NETWORK_MESSAGE, 0);
  }
  const detail = (err.error as { detail?: unknown } | null)?.detail;
  return new CostingApiError(typeof detail === 'string' && detail ? detail : GENERIC_MESSAGE, err.status);
}

export function toMovementValuation(dto: MovementValuationDto): MovementValuation {
  return {
    id: dto.id,
    movementId: dto.movement_id,
    productId: dto.product_id,
    productName: dto.product_name,
    unitAbbreviation: dto.unit_abbreviation,
    kind: dto.kind,
    quantity: dto.quantity,
    unitCost: dto.unit_cost,
    value: dto.value,
    averageBefore: dto.average_before,
    averageAfter: dto.average_after,
    costOrigin: dto.cost_origin,
    sourceType: dto.source_type,
    sourceId: dto.source_id,
    sourceLabel: dto.source_label,
    occurredAt: dto.occurred_at,
  };
}

/** Snapshots de valoración de movimientos (`/api/valuation/movements/`, solo lectura, módulo Costeo). */
@Injectable({
  providedIn: 'root',
})
export class MovementValuationApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/valuation/movements/`;

  list(params: MovementValuationParams = {}): Observable<Page<MovementValuation>> {
    let httpParams = new HttpParams();
    if (params.dateFrom) httpParams = httpParams.set('date_from', params.dateFrom);
    if (params.dateTo) httpParams = httpParams.set('date_to', params.dateTo);
    if (params.productId) httpParams = httpParams.set('product_id', params.productId);
    if (params.movementId) httpParams = httpParams.set('movement_id', params.movementId);
    if (params.sourceType) httpParams = httpParams.set('source_type', params.sourceType);
    if (params.sourceType && params.sourceId) httpParams = httpParams.set('source_id', params.sourceId);
    if (params.page !== undefined) httpParams = httpParams.set('page', String(params.page));
    if (params.pageSize !== undefined) httpParams = httpParams.set('page_size', String(params.pageSize));
    return this.http.get<Page<MovementValuationDto>>(this.baseUrl, { params: httpParams }).pipe(
      map((page): Page<MovementValuation> => ({ ...page, results: page.results.map(toMovementValuation) })),
      catchError((err: HttpErrorResponse) => throwError(() => toError(err))),
    );
  }
}
