import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import { toApiError } from '../models/api-error';
import {
  MovementsPage,
  MovementsPageDto,
  OpeningInput,
  OpeningResult,
  OpeningResultDto,
  StockBalance,
  StockBalanceDto,
  StockListParams,
  StockMovement,
  StockMovementDto,
  StockUnit,
  StockUnitDto,
} from '../models/stock';

function toUnit(dto: StockUnitDto | null): StockUnit | null {
  return dto ? { name: dto.name, abbreviation: dto.abbreviation, allowsFractions: dto.allows_fractions } : null;
}

export function toBalance(dto: StockBalanceDto): StockBalance {
  return {
    productId: dto.product_id,
    productName: dto.product_name,
    warehouseId: dto.warehouse_id,
    warehouseName: dto.warehouse_name,
    quantity: dto.quantity,
    unit: toUnit(dto.unit),
  };
}

function toMovement(dto: StockMovementDto): StockMovement {
  return {
    id: dto.id,
    movementType: dto.movement_type,
    quantity: dto.quantity,
    movementDate: dto.movement_date,
    reference: dto.reference,
    createdAt: dto.created_at,
  };
}

function toResult(dto: OpeningResultDto): OpeningResult {
  return {
    openingId: dto.opening_id,
    warehouseId: dto.warehouse_id,
    movementDate: dto.movement_date,
    reference: dto.reference,
    lines: dto.lines.map((line) => ({
      productId: line.product_id,
      quantity: line.quantity,
      movementId: line.movement_id,
    })),
  };
}

/** Existencias, movimientos y apertura de stock (`/api/stock/`). */
@Injectable({
  providedIn: 'root',
})
export class StockApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/stock/`;

  list(params: StockListParams = {}): Observable<Page<StockBalance>> {
    let httpParams = new HttpParams();
    if (params.warehouseId) httpParams = httpParams.set('warehouse_id', params.warehouseId);
    if (params.page !== undefined) httpParams = httpParams.set('page', String(params.page));
    if (params.pageSize !== undefined) httpParams = httpParams.set('page_size', String(params.pageSize));
    return this.http.get<Page<StockBalanceDto>>(this.baseUrl, { params: httpParams }).pipe(
      map((page): Page<StockBalance> => ({ ...page, results: page.results.map(toBalance) })),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }

  movements(warehouseId: string, productId: string, page = 1, pageSize = 20): Observable<MovementsPage> {
    const params = new HttpParams()
      .set('warehouse_id', warehouseId)
      .set('product_id', productId)
      .set('page', String(page))
      .set('page_size', String(pageSize));
    return this.http.get<MovementsPageDto>(`${this.baseUrl}movements/`, { params }).pipe(
      map(
        (body): MovementsPage => ({
          count: body.count,
          results: body.results.map(toMovement),
          summary: {
            productId: body.summary.product_id,
            productName: body.summary.product_name,
            warehouseId: body.summary.warehouse_id,
            warehouseName: body.summary.warehouse_name,
            quantity: body.summary.quantity,
            unit: toUnit(body.summary.unit),
          },
        }),
      ),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }

  /** Ids (de los consultados) que ya tienen movimientos en el almacén: no admiten apertura. */
  productsWithHistory(warehouseId: string, productIds: string[]): Observable<string[]> {
    let params = new HttpParams().set('warehouse_id', warehouseId);
    for (const id of productIds) {
      params = params.append('product_id', id);
    }
    return this.http.get<{ products_with_history: string[] }>(`${this.baseUrl}opening-check/`, { params }).pipe(
      map((body) => body.products_with_history),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }

  /** Confirma la apertura; reenviar el mismo `openingId` devuelve la apertura original sin duplicarla. */
  register(input: OpeningInput): Observable<OpeningResult> {
    const body = {
      opening_id: input.openingId,
      warehouse_id: input.warehouseId,
      movement_date: input.movementDate,
      reference: input.reference,
      lines: input.lines.map((line) => ({ product_id: line.productId, quantity: line.quantity })),
    };
    return this.http.post<OpeningResultDto>(`${this.baseUrl}openings/`, body).pipe(
      map(toResult),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }
}
