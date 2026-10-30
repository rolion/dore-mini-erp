import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import {
  Receipt,
  ReceiptApiError,
  ReceiptDto,
  ReceiptFieldErrors,
  ReceiptInput,
  ReceiptSummary,
  ReceiptSummaryDto,
  ReceptionForm,
  ReceptionFormDto,
} from '../models/receipt';

export const RECEIPT_NETWORK_ERROR_MESSAGE = 'No se pudo conectar con el servidor. Inténtalo de nuevo.';
export const RECEIPT_NOT_FOUND_MESSAGE = 'No se encontró la compra o la recepción.';
export const RECEIPT_NOT_RECEIVABLE_MESSAGE = 'Solo una compra confirmada admite recepciones.';
export const RECEIPT_GENERIC_ERROR_MESSAGE = 'Ocurrió un error inesperado. Inténtalo de nuevo.';
export const RECEIPT_VALIDATION_ERROR_MESSAGE = 'Revisa los datos ingresados.';

function messages(value: unknown): string | undefined {
  return Array.isArray(value) && value.length ? value.map(String).join(' ') : undefined;
}

/** Errores 400: `receipt_date`, `warehouse_id`, `lines` (mensaje general o un objeto por línea). */
export function toReceiptFieldErrors(body: unknown): ReceiptFieldErrors {
  const errors: ReceiptFieldErrors = { lines: [] };
  if (!body || typeof body !== 'object') return errors;
  const record = body as Record<string, unknown>;
  errors.receiptDate = messages(record['receipt_date']);
  errors.warehouseId = messages(record['warehouse_id']);
  const lines = record['lines'];
  if (Array.isArray(lines) && lines.some((line) => typeof line === 'string')) {
    errors.linesMessage = lines.map(String).join(' ');
  } else if (Array.isArray(lines)) {
    errors.lines = lines.map((line) => {
      const source = line && typeof line === 'object' ? (line as Record<string, unknown>) : {};
      return { itemId: messages(source['item_id']), quantity: messages(source['quantity']) };
    });
  }
  return errors;
}

function toError(err: HttpErrorResponse): ReceiptApiError {
  if (err.status === 0) return new ReceiptApiError(RECEIPT_NETWORK_ERROR_MESSAGE, 0);
  if (err.status === 400) {
    const general = messages((err.error as Record<string, unknown> | null)?.['non_field_errors']);
    return new ReceiptApiError(general ?? RECEIPT_VALIDATION_ERROR_MESSAGE, 400, toReceiptFieldErrors(err.error));
  }
  if (err.status === 404) return new ReceiptApiError(RECEIPT_NOT_FOUND_MESSAGE, 404);
  if (err.status === 409) {
    const detail = (err.error as { detail?: unknown } | null)?.detail;
    return new ReceiptApiError(typeof detail === 'string' ? detail : RECEIPT_NOT_RECEIVABLE_MESSAGE, 409);
  }
  return new ReceiptApiError(RECEIPT_GENERIC_ERROR_MESSAGE, err.status);
}

function toReceipt(dto: ReceiptDto): Receipt {
  return {
    id: dto.id,
    reference: dto.reference,
    purchase: dto.purchase,
    receiptDate: dto.receipt_date,
    status: dto.status,
    userName: dto.user_name,
    createdAt: dto.created_at,
    warehouse: dto.warehouse,
    lines: dto.lines.map((line) => ({
      itemId: line.item_id,
      productId: line.product.id,
      productName: line.product.name,
      unitAbbreviation: line.unit.abbreviation,
      quantity: line.quantity,
    })),
    movements: dto.movements
      ? dto.movements.map((m) => ({
          id: m.id,
          productName: m.product.name,
          warehouseName: m.warehouse.name,
          quantity: m.quantity,
          unitAbbreviation: m.unit.abbreviation,
        }))
      : null,
  };
}

function toSummary(dto: ReceiptSummaryDto): ReceiptSummary {
  return {
    id: dto.id,
    reference: dto.reference,
    receiptDate: dto.receipt_date,
    status: dto.status,
    userName: dto.user_name,
    linesCount: dto.lines_count,
  };
}

function toForm(dto: ReceptionFormDto): ReceptionForm {
  return {
    inventoryEnabled: dto.inventory_enabled,
    warehouses: dto.warehouses.map((w) => ({ id: w.id, name: w.name, isDefault: w.is_default })),
    warehouseId: dto.warehouse_id,
    lines: dto.lines.map((line) => ({
      itemId: line.item_id,
      productId: line.product.id,
      productName: line.product.name,
      unitAbbreviation: line.unit.abbreviation,
      allowsFractions: line.allows_fractions,
      tracksStock: line.tracks_stock,
      ordered: line.ordered,
      received: line.received,
      pending: line.pending,
    })),
  };
}

@Injectable({
  providedIn: 'root',
})
export class ReceiptsApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/purchases/`;

  receptionForm(purchaseId: string): Observable<ReceptionForm> {
    return this.http.get<ReceptionFormDto>(`${this.baseUrl}${purchaseId}/reception-form/`).pipe(
      map(toForm),
      catchError((err: HttpErrorResponse) => throwError(() => toError(err))),
    );
  }

  list(purchaseId: string): Observable<Page<ReceiptSummary>> {
    return this.http.get<Page<ReceiptSummaryDto>>(`${this.baseUrl}${purchaseId}/receipts/`).pipe(
      map((page): Page<ReceiptSummary> => ({ ...page, results: page.results.map(toSummary) })),
      catchError((err: HttpErrorResponse) => throwError(() => toError(err))),
    );
  }

  get(purchaseId: string, receiptId: string): Observable<Receipt> {
    return this.http.get<ReceiptDto>(`${this.baseUrl}${purchaseId}/receipts/${receiptId}/`).pipe(
      map(toReceipt),
      catchError((err: HttpErrorResponse) => throwError(() => toError(err))),
    );
  }

  /** Registra la recepción; repetir el mismo `receiptId` devuelve la ya registrada. */
  create(purchaseId: string, input: ReceiptInput): Observable<Receipt> {
    const body: Record<string, unknown> = {
      receipt_id: input.receiptId,
      receipt_date: input.receiptDate,
      lines: input.lines.map((line) => ({ item_id: line.itemId, quantity: line.quantity })),
    };
    if (input.warehouseId) body['warehouse_id'] = input.warehouseId;
    return this.http.post<ReceiptDto>(`${this.baseUrl}${purchaseId}/receipts/`, body).pipe(
      map(toReceipt),
      catchError((err: HttpErrorResponse) => throwError(() => toError(err))),
    );
  }
}
