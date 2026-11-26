import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { tr } from '../../../core/i18n/translate';
import { Page } from '../../../shared/models/page';
import {
  OrderApiError, OrderCreateInput, OrderFieldErrors, OrderStatusFilter, OrderUpdateInput, OrderWarehouse, OrderWarehouseDto,
  ProductionOrder, ProductionOrderDto,
} from '../models/order';

function fromDto(dto: ProductionOrderDto): ProductionOrder {
  return {
    id: dto.id,
    number: dto.number,
    status: dto.status,
    recipe: dto.recipe,
    resultProduct: dto.result_product,
    warehouse: dto.warehouse,
    preparations: dto.preparations,
    yieldPerPreparation: dto.yield_per_preparation,
    expectedOutput: dto.expected_output,
    ingredients: dto.ingredients.map(line => ({
      productId: line.product_id, productName: line.product_name, unitId: line.unit_id,
      unitAbbreviation: line.unit_abbreviation, quantityPerPreparation: line.quantity_per_preparation,
      expectedQuantity: line.expected_quantity,
    })),
    createdAt: dto.created_at,
    startedAt: dto.started_at,
  };
}

function text(value: unknown): string | undefined {
  if (Array.isArray(value)) return value.map(String).join(' ');
  return typeof value === 'string' ? value : undefined;
}

function fieldErrors(body: unknown): OrderFieldErrors {
  if (!body || typeof body !== 'object') return {};
  const record = body as Record<string, unknown>;
  return {
    recipeId: text(record['recipe_id']), warehouseId: text(record['warehouse_id']),
    preparations: text(record['preparations']), detail: text(record['detail']),
  };
}

function apiError(error: HttpErrorResponse): Observable<never> {
  const body: unknown = error.error;
  const fields = fieldErrors(body);
  const invalidPage = error.status === 400 && !!body && typeof body === 'object' && Array.isArray((body as Record<string, unknown>)['page']);
  const message = error.status === 0 ? tr('PRODUCTION.ORDERS.ERRORS.NETWORK')
    : error.status === 400 ? tr('PRODUCTION.ORDERS.ERRORS.VALIDATION')
    : error.status === 403 ? tr('PRODUCTION.ORDERS.ERRORS.FORBIDDEN')
    : error.status === 404 ? tr('PRODUCTION.ORDERS.ERRORS.NOT_FOUND')
    : error.status === 409 ? (fields.detail ?? tr('PRODUCTION.ORDERS.ERRORS.CONFLICT')) : tr('PRODUCTION.ORDERS.ERRORS.GENERIC');
  return throwError(() => new OrderApiError(message, error.status, fields, invalidPage));
}

@Injectable({ providedIn: 'root' })
export class OrdersApiService {
  private http = inject(HttpClient);
  private url = `${environment.apiUrl}/production-orders/`;

  list(params: { status?: OrderStatusFilter; page?: number; pageSize?: number } = {}): Observable<Page<ProductionOrder>> {
    let query = new HttpParams();
    if (params.status) query = query.set('status', params.status);
    if (params.page) query = query.set('page', params.page);
    if (params.pageSize) query = query.set('page_size', params.pageSize);
    return this.http.get<Page<ProductionOrderDto>>(this.url, { params: query }).pipe(
      map(page => ({ ...page, results: page.results.map(fromDto) })), catchError(apiError));
  }

  get(id: string): Observable<ProductionOrder> {
    return this.request(this.http.get<ProductionOrderDto>(`${this.url}${id}/`));
  }

  create(input: OrderCreateInput): Observable<ProductionOrder> {
    return this.request(this.http.post<ProductionOrderDto>(this.url,
      { recipe_id: input.recipeId, warehouse_id: input.warehouseId, preparations: input.preparations }));
  }

  update(id: string, input: OrderUpdateInput): Observable<ProductionOrder> {
    return this.request(this.http.put<ProductionOrderDto>(`${this.url}${id}/`,
      { warehouse_id: input.warehouseId, preparations: input.preparations }));
  }

  start(id: string): Observable<ProductionOrder> {
    return this.request(this.http.post<ProductionOrderDto>(`${this.url}${id}/start/`, {}));
  }

  warehouses(): Observable<OrderWarehouse[]> {
    return this.http.get<OrderWarehouseDto[]>(`${this.url}warehouses/`).pipe(
      map(items => items.map(item => ({ id: item.id, name: item.name, isDefault: item.is_default }))), catchError(apiError));
  }

  private request(source: Observable<ProductionOrderDto>): Observable<ProductionOrder> {
    return source.pipe(map(fromDto), catchError(apiError));
  }
}

@Injectable({ providedIn: 'root' })
export class OrderFiltersState {
  status: OrderStatusFilter = 'all';
  pageIndex = 0;
}
