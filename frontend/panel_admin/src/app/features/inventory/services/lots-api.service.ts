import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import { toApiError } from '../models/api-error';
import { LotListParams, StockLot, StockLotDto } from '../models/lot';

export function toLot(dto: StockLotDto): StockLot {
  return {
    id: dto.id,
    code: dto.code,
    status: dto.status,
    lotDate: dto.lot_date,
    fiscalPeriodName: dto.fiscal_period_name,
    productId: dto.product_id,
    productName: dto.product_name,
    productActive: dto.product_active,
    unit: dto.unit ? { abbreviation: dto.unit.abbreviation, allowsFractions: dto.unit.allows_fractions } : null,
    warehouseId: dto.warehouse_id,
    warehouseName: dto.warehouse_name,
    physicalQuantity: dto.physical_quantity,
    availableQuantity: dto.available_quantity,
    createdAt: dto.created_at,
    releasedAt: dto.released_at,
    releasedByName: dto.released_by_name,
  };
}

/** Lotes de inventario: solo lectura (los crea y libera Producción desde el servidor). */
@Injectable({
  providedIn: 'root',
})
export class LotsApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/stock-lots/`;

  list(params: LotListParams = {}): Observable<Page<StockLot>> {
    let httpParams = new HttpParams();
    if (params.search) httpParams = httpParams.set('search', params.search);
    if (params.productId) httpParams = httpParams.set('product_id', params.productId);
    if (params.warehouseId) httpParams = httpParams.set('warehouse_id', params.warehouseId);
    if (params.status) httpParams = httpParams.set('status', params.status);
    if (params.withStock) httpParams = httpParams.set('with_stock', 'true');
    if (params.page !== undefined) httpParams = httpParams.set('page', String(params.page));
    if (params.pageSize !== undefined) httpParams = httpParams.set('page_size', String(params.pageSize));
    return this.http.get<Page<StockLotDto>>(this.baseUrl, { params: httpParams }).pipe(
      map((page): Page<StockLot> => ({ ...page, results: page.results.map(toLot) })),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }
}
