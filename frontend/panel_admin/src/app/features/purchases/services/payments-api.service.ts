import { tr } from '../../../core/i18n/translate';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import {
  Payment,
  PaymentApiError,
  PaymentDto,
  PaymentFieldErrors,
  PaymentInput,
  PaymentPostingIssue,
  PaymentPreview,
  PaymentPreviewDto,
} from '../models/payment';

export const PAYMENT_NETWORK_ERROR_MESSAGE = (): string => tr('CUSTOMERS.CUSTOMERS_API_SERVICE.NO_SE_PUDO_CONECTAR_CON');
export const PAYMENT_NOT_FOUND_MESSAGE = (): string => tr('PURCHASES.PAYMENTS_API_SERVICE.NO_SE_ENCONTRO_LA_COMPRA');
export const PAYMENT_NOT_PAYABLE_MESSAGE = (): string => tr('PURCHASES.PAYMENTS_API_SERVICE.SOLO_UNA_COMPRA_CONFIRMADA_ADMITE');
export const PAYMENT_GENERIC_ERROR_MESSAGE = (): string => tr('CUSTOMERS.CUSTOMERS_API_SERVICE.OCURRIO_UN_ERROR_INESPERADO_INTENTALO');
export const PAYMENT_VALIDATION_ERROR_MESSAGE = (): string => tr('CUSTOMERS.CUSTOMERS_API_SERVICE.REVISA_LOS_DATOS_INGRESADOS');

function messages(value: unknown): string | undefined {
  return Array.isArray(value) && value.length ? value.map(String).join(' ') : undefined;
}

/** Errores 400: `amount`, `payment_method`, `payment_date`. */
export function toPaymentFieldErrors(body: unknown): PaymentFieldErrors {
  if (!body || typeof body !== 'object') return {};
  const record = body as Record<string, unknown>;
  return {
    amount: messages(record['amount']),
    paymentMethod: messages(record['payment_method']),
    paymentDate: messages(record['payment_date']),
  };
}

function toPostingIssues(body: unknown): PaymentPostingIssue[] {
  const raw = (body as { issues?: unknown } | null)?.issues;
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((item): item is { code?: string; subject?: string; message: string } =>
      !!item && typeof item === 'object' && typeof (item as { message?: unknown }).message === 'string')
    .map((item) => ({ code: String(item.code ?? ''), subject: String(item.subject ?? ''), message: item.message }));
}

function toPreview(dto: PaymentPreviewDto): PaymentPreview {
  return {
    covered: dto.covered,
    debtAmount: dto.debt_amount,
    advanceAmount: dto.advance_amount,
    lines: dto.lines.map((line) => ({ side: line.side, role: line.role, accountName: line.account.name, amount: line.amount })),
    issues: toPostingIssues(dto),
  };
}

function toError(err: HttpErrorResponse): PaymentApiError {
  if (err.status === 0) return new PaymentApiError(PAYMENT_NETWORK_ERROR_MESSAGE(), 0);
  if (err.status === 400) {
    const general = messages((err.error as Record<string, unknown> | null)?.['non_field_errors']);
    const code = (err.error as { code?: unknown } | null)?.code;
    return new PaymentApiError(general ?? PAYMENT_VALIDATION_ERROR_MESSAGE(), 400, toPaymentFieldErrors(err.error),
      typeof code === 'string' ? code : null);
  }
  if (err.status === 404) return new PaymentApiError(PAYMENT_NOT_FOUND_MESSAGE(), 404);
  if (err.status === 409) {
    const body = (err.error ?? {}) as { detail?: unknown; code?: unknown };
    const code = typeof body.code === 'string' ? body.code : null;
    return new PaymentApiError(
      typeof body.detail === 'string' ? body.detail : PAYMENT_NOT_PAYABLE_MESSAGE(), 409, {}, code,
      code === 'posting_configuration_missing' ? toPostingIssues(err.error) : [],
    );
  }
  return new PaymentApiError(PAYMENT_GENERIC_ERROR_MESSAGE(), err.status);
}

function toPayment(dto: PaymentDto): Payment {
  return {
    id: dto.id,
    reference: dto.reference,
    amount: dto.amount,
    paymentMethod: dto.payment_method,
    paymentDate: dto.payment_date,
    status: dto.status,
    userName: dto.user_name,
    createdAt: dto.created_at,
    debtAmount: dto.debt_amount ?? dto.amount,
    advanceAmount: dto.advance_amount ?? '0.00',
    accountingEntries: (dto.accounting_entries ?? []).map((entry) => ({
      id: entry.id,
      kind: entry.kind,
      accountingDate: entry.accounting_date,
      total: entry.total,
    })),
  };
}

@Injectable({
  providedIn: 'root',
})
export class PaymentsApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/purchases/`;

  list(purchaseId: string): Observable<Page<Payment>> {
    return this.http.get<Page<PaymentDto>>(`${this.baseUrl}${purchaseId}/payments/`).pipe(
      map((page): Page<Payment> => ({ ...page, results: page.results.map(toPayment) })),
      catchError((err: HttpErrorResponse) => throwError(() => toError(err))),
    );
  }

  /** Asiento previsto de un pago (reparto deuda/anticipo y líneas Debe/Haber); no escribe nada. */
  preview(purchaseId: string, input: Pick<PaymentInput, 'amount' | 'paymentMethod' | 'paymentDate'>): Observable<PaymentPreview> {
    const params = { amount: input.amount, payment_method: input.paymentMethod, payment_date: input.paymentDate };
    return this.http.get<PaymentPreviewDto>(`${this.baseUrl}${purchaseId}/payments/preview/`, { params }).pipe(
      map(toPreview),
      catchError((err: HttpErrorResponse) => throwError(() => toError(err))),
    );
  }

  /** Registra el pago; repetir el mismo `paymentId` devuelve el ya registrado. */
  create(purchaseId: string, input: PaymentInput): Observable<Payment> {
    const body = {
      payment_id: input.paymentId,
      amount: input.amount,
      payment_method: input.paymentMethod,
      payment_date: input.paymentDate,
    };
    return this.http.post<PaymentDto>(`${this.baseUrl}${purchaseId}/payments/`, body).pipe(
      map(toPayment),
      catchError((err: HttpErrorResponse) => throwError(() => toError(err))),
    );
  }
}
