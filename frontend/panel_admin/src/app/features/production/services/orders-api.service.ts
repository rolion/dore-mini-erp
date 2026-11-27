import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { tr } from '../../../core/i18n/translate';
import { Page } from '../../../shared/models/page';
import {
  OrderApiError, OrderCreateInput, OrderFieldErrors, OrderShortage, OrderStatusFilter, OrderUpdateInput, OrderWarehouse,
  OrderWarehouseDto, PackInput, ProductionOrder, ProductionOrderDto, RefrigerateInput,
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
      expectedQuantity: line.expected_quantity, actualQuantity: line.actual_quantity,
    })),
    createdAt: dto.created_at,
    startedAt: dto.started_at,
    actualOutput: dto.actual_output,
    enteredAt: dto.entered_at,
    lot: dto.lot,
    costTotal: dto.cost_total,
    release: dto.release
      ? { minHours: dto.release.min_hours, releasableFrom: dto.release.releasable_from, canRelease: dto.release.can_release }
      : null,
    releasedAt: dto.released_at,
    releasedBy: dto.released_by,
    packing: dto.packing ? {
      unitsPerPack: dto.packing.units_per_pack, bagsPerPack: dto.packing.bags_per_pack,
      labelsPerPack: dto.packing.labels_per_pack,
      bulkAvailable: dto.packing.bulk_available, bulkUnitAbbreviation: dto.packing.bulk_unit_abbreviation,
      packings: dto.packing.packings.map(entry => ({
        id: entry.id, number: entry.number, packs: entry.packs, packProduct: entry.pack_product,
        bagProduct: entry.bag_product, labelProduct: entry.label_product, bulkQuantity: entry.bulk_quantity,
        bagsQuantity: entry.bags_quantity, labelsQuantity: entry.labels_quantity,
        lot: entry.lot, costTotal: entry.cost_total, unitCost: entry.unit_cost, createdAt: entry.created_at,
        createdBy: entry.created_by,
      })),
    } : null,
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
    packs: text(record['packs']), packProductId: text(record['pack_product_id']),
    bagProductId: text(record['bag_product_id']), labelProductId: text(record['label_product_id']),
    requestId: text(record['request_id']),
    actualOutput: text(record['actual_output']), enteredAt: text(record['entered_at']),
    ingredients: ingredientsText(record['ingredients']), ingredientLines: ingredientLines(record['ingredients']), code: typeof record['code'] === 'string' ? record['code'] : undefined,
    releasableFrom: typeof record['releasable_from'] === 'string' ? record['releasable_from'] : undefined,
  };
}

/** Errores de `ingredients` que no son de una línea: texto suelto o mensajes sueltos de la lista. */
function ingredientsText(value: unknown): string | undefined {
  if (!Array.isArray(value)) return text(value);
  const messages = value.filter(item => typeof item === 'string').map(item => text(item));
  return messages.filter((message): message is string => !!message).join(' ') || undefined;
}

/** Errores por línea (`actual_quantity`) en el orden de la lista; `undefined` si ninguna tiene error. */
function ingredientLines(value: unknown): (string | undefined)[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const lines = value.map(item => (item && typeof item === 'object' ? text((item as Record<string, unknown>)['actual_quantity']) : undefined));
  return lines.some(message => !!message) ? lines : undefined;
}

function shortagesOf(body: unknown): OrderShortage[] {
  const list = body && typeof body === 'object' ? (body as Record<string, unknown>)['shortages'] : null;
  if (!Array.isArray(list)) return [];
  return list.map(raw => {
    const item = raw as Record<string, string | null>;
    return {
      productId: String(item['product_id']), productName: String(item['product_name'] ?? ''),
      unitAbbreviation: item['unit_abbreviation'] ?? null, requested: String(item['requested']),
      available: String(item['available']), missing: String(item['missing']),
    };
  });
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
  return throwError(() => new OrderApiError(message, error.status, fields, invalidPage, shortagesOf(body)));
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

  refrigerate(id: string, input: RefrigerateInput): Observable<ProductionOrder> {
    return this.request(this.http.post<ProductionOrderDto>(`${this.url}${id}/refrigerate/`, {
      entered_at: input.enteredAt, actual_output: input.actualOutput,
      ingredients: input.ingredients.map(line => ({ product_id: line.productId, actual_quantity: line.actualQuantity })),
    }));
  }

  release(id: string): Observable<ProductionOrder> {
    return this.request(this.http.post<ProductionOrderDto>(`${this.url}${id}/release/`, {}));
  }

  pack(id: string, input: PackInput): Observable<ProductionOrder> {
    return this.request(this.http.post<ProductionOrderDto>(`${this.url}${id}/pack/`, {
      request_id: input.requestId, packs: input.packs, pack_product_id: input.packProductId,
      bag_product_id: input.bagProductId, label_product_id: input.labelProductId,
    }));
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
