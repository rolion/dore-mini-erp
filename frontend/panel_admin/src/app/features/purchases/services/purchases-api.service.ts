import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import {
  HeaderField,
  ItemErrors,
  ItemField,
  Purchase,
  PurchaseApiError,
  PurchaseDto,
  PurchaseFieldErrors,
  PurchaseInput,
  PurchaseItemDto,
  PurchaseItem,
  PurchaseListParams,
  PurchaseSummary,
  PurchaseSummaryDto,
} from '../models/purchase';

export const NETWORK_ERROR_MESSAGE = 'No se pudo conectar con el servidor. Inténtalo de nuevo.';
export const NOT_FOUND_MESSAGE = 'Compra no encontrada.';
export const NOT_EDITABLE_MESSAGE = 'La compra ya no admite cambios.';
export const GENERIC_ERROR_MESSAGE = 'Ocurrió un error inesperado. Inténtalo de nuevo.';
export const VALIDATION_ERROR_MESSAGE = 'Revisa los datos ingresados.';

const HEADER_FIELDS: Readonly<Record<string, HeaderField>> = {
  supplier_id: 'supplierId',
  purchase_date: 'purchaseDate',
  external_reference: 'externalReference',
  notes: 'notes',
};
const ITEM_FIELDS: Readonly<Record<string, ItemField>> = {
  product_id: 'productId',
  quantity: 'quantity',
  unit_price: 'unitPrice',
};

function toItem(dto: PurchaseItemDto): PurchaseItem {
  return {
    id: dto.id,
    productId: dto.product_id,
    productName: dto.product_name,
    unitAbbreviation: dto.unit_abbreviation,
    quantity: dto.quantity,
    unitPrice: dto.unit_price,
    subtotal: dto.subtotal,
  };
}

function toPurchase(dto: PurchaseDto): Purchase {
  return {
    id: dto.id,
    supplier: dto.supplier,
    purchaseDate: dto.purchase_date,
    externalReference: dto.external_reference,
    notes: dto.notes,
    status: dto.status,
    currency: dto.currency,
    editable: dto.editable,
    items: dto.items.map(toItem),
    total: dto.total,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function toSummary(dto: PurchaseSummaryDto): PurchaseSummary {
  return {
    id: dto.id,
    purchaseDate: dto.purchase_date,
    supplier: dto.supplier,
    externalReference: dto.external_reference,
    total: dto.total,
    currency: dto.currency,
    status: dto.status,
    itemsCount: dto.items_count,
  };
}

function toBody(input: Partial<PurchaseInput>): Record<string, unknown> {
  const body: Record<string, unknown> = {};
  if (input.supplierId !== undefined) body['supplier_id'] = input.supplierId;
  if (input.purchaseDate !== undefined) body['purchase_date'] = input.purchaseDate;
  if (input.externalReference !== undefined) body['external_reference'] = input.externalReference;
  if (input.notes !== undefined) body['notes'] = input.notes;
  if (input.items !== undefined) {
    body['items'] = input.items.map((item) => ({
      product_id: item.productId,
      quantity: item.quantity,
      unit_price: item.unitPrice,
    }));
  }
  return body;
}

function messages(value: unknown): string | undefined {
  return Array.isArray(value) && value.length ? value.map(String).join(' ') : undefined;
}

/** Errores 400: cabecera por campo y un objeto por línea (`items: [{}, {quantity: [...]}]`). */
export function toFieldErrors(body: unknown): PurchaseFieldErrors {
  const errors: PurchaseFieldErrors = { header: {}, items: [] };
  if (!body || typeof body !== 'object') return errors;
  const record = body as Record<string, unknown>;
  for (const [api, field] of Object.entries(HEADER_FIELDS)) {
    const message = messages(record[api]);
    if (message) errors.header[field] = message;
  }
  const items = record['items'];
  if (Array.isArray(items) && items.some((line) => typeof line === 'string')) {
    errors.itemsMessage = items.map(String).join(' ');
  } else if (Array.isArray(items)) {
    errors.items = items.map((line): ItemErrors => {
      const lineErrors: ItemErrors = {};
      if (line && typeof line === 'object') {
        for (const [api, field] of Object.entries(ITEM_FIELDS)) {
          const message = messages((line as Record<string, unknown>)[api]);
          if (message) lineErrors[field] = message;
        }
      }
      return lineErrors;
    });
  }
  return errors;
}

function toApiError(err: HttpErrorResponse): PurchaseApiError {
  if (err.status === 0) return new PurchaseApiError(NETWORK_ERROR_MESSAGE, 0);
  if (err.status === 400) {
    return new PurchaseApiError(VALIDATION_ERROR_MESSAGE, 400, toFieldErrors(err.error));
  }
  if (err.status === 404) return new PurchaseApiError(NOT_FOUND_MESSAGE, 404);
  if (err.status === 409) return new PurchaseApiError(NOT_EDITABLE_MESSAGE, 409);
  return new PurchaseApiError(GENERIC_ERROR_MESSAGE, err.status);
}

@Injectable({
  providedIn: 'root',
})
export class PurchasesApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/purchases/`;

  list(params: PurchaseListParams = {}): Observable<Page<PurchaseSummary>> {
    let httpParams = new HttpParams();
    if (params.supplierId) httpParams = httpParams.set('supplier_id', params.supplierId);
    if (params.page !== undefined) httpParams = httpParams.set('page', String(params.page));
    if (params.pageSize !== undefined) httpParams = httpParams.set('page_size', String(params.pageSize));
    return this.http.get<Page<PurchaseSummaryDto>>(this.baseUrl, { params: httpParams }).pipe(
      map((page): Page<PurchaseSummary> => ({ ...page, results: page.results.map(toSummary) })),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err))),
    );
  }

  get(id: string): Observable<Purchase> {
    return this.request(this.http.get<PurchaseDto>(`${this.baseUrl}${id}/`));
  }

  create(input: PurchaseInput): Observable<Purchase> {
    return this.request(this.http.post<PurchaseDto>(this.baseUrl, toBody(input)));
  }

  update(id: string, input: Partial<PurchaseInput>): Observable<Purchase> {
    return this.request(this.http.patch<PurchaseDto>(`${this.baseUrl}${id}/`, toBody(input)));
  }

  private request(source: Observable<PurchaseDto>): Observable<Purchase> {
    return source.pipe(
      map(toPurchase),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err))),
    );
  }
}
