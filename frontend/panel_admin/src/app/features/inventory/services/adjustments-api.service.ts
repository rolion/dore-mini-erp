import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import {
  AdjustmentBalance,
  AdjustmentBalanceDto,
  AdjustmentInput,
  AdjustmentListParams,
  StockAdjustment,
  StockAdjustmentDetail,
  StockAdjustmentDetailDto,
  StockAdjustmentDto,
} from '../models/adjustment';
import { toApiError } from '../models/api-error';

export function toAdjustment(dto: StockAdjustmentDto): StockAdjustment {
  return {
    id: dto.id,
    reference: dto.reference,
    createdAt: dto.created_at,
    product: dto.product,
    warehouse: dto.warehouse,
    systemQuantity: dto.system_quantity,
    countedQuantity: dto.counted_quantity,
    difference: dto.difference,
    kind: dto.kind,
    unitAbbreviation: dto.unit.abbreviation,
    user: dto.user,
    status: dto.status,
  };
}

export function toAdjustmentDetail(dto: StockAdjustmentDetailDto): StockAdjustmentDetail {
  return { ...toAdjustment(dto), reason: dto.reason, movementId: dto.movement.id };
}

/** Ajustes de existencias (`/api/stock-adjustments/`): se crean y se consultan, nunca se editan ni se borran. */
@Injectable({
  providedIn: 'root',
})
export class AdjustmentsApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/stock-adjustments/`;

  list(params: AdjustmentListParams = {}): Observable<Page<StockAdjustment>> {
    let httpParams = new HttpParams();
    if (params.dateFrom) httpParams = httpParams.set('date_from', params.dateFrom);
    if (params.dateTo) httpParams = httpParams.set('date_to', params.dateTo);
    if (params.productId) httpParams = httpParams.set('product_id', params.productId);
    if (params.warehouseId) httpParams = httpParams.set('warehouse_id', params.warehouseId);
    if (params.page !== undefined) httpParams = httpParams.set('page', String(params.page));
    if (params.pageSize !== undefined) httpParams = httpParams.set('page_size', String(params.pageSize));
    return this.http.get<Page<StockAdjustmentDto>>(this.baseUrl, { params: httpParams }).pipe(
      map((page): Page<StockAdjustment> => ({ ...page, results: page.results.map(toAdjustment) })),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }

  get(id: string): Observable<StockAdjustmentDetail> {
    return this.http.get<StockAdjustmentDetailDto>(`${this.baseUrl}${id}/`).pipe(
      map(toAdjustmentDetail),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }

  /** Saldo vigente del producto en el almacén y su unidad (0 si aún no hay movimientos). */
  balance(productId: string, warehouseId: string): Observable<AdjustmentBalance> {
    const params = new HttpParams().set('product_id', productId).set('warehouse_id', warehouseId);
    return this.http.get<AdjustmentBalanceDto>(`${this.baseUrl}balance/`, { params }).pipe(
      map((dto): AdjustmentBalance => ({
        systemQuantity: dto.system_quantity,
        unit: dto.unit ? { abbreviation: dto.unit.abbreviation, allowsFractions: dto.unit.allows_fractions } : null,
      })),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }

  /** Confirma el ajuste; reenviar el mismo `adjustmentId` devuelve el original sin duplicarlo. */
  confirm(input: AdjustmentInput): Observable<StockAdjustmentDetail> {
    const body = {
      adjustment_id: input.adjustmentId,
      product_id: input.productId,
      warehouse_id: input.warehouseId,
      counted_quantity: input.countedQuantity,
      expected_system_quantity: input.expectedSystemQuantity,
      reason: input.reason,
    };
    return this.http.post<StockAdjustmentDetailDto>(this.baseUrl, body).pipe(
      map(toAdjustmentDetail),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }
}
