import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import { Payment, PaymentApiError, PaymentDto, PaymentFieldErrors, PaymentInput } from '../models/payment';

export const PAYMENT_NETWORK_ERROR_MESSAGE = 'No se pudo conectar con el servidor. Inténtalo de nuevo.';
export const PAYMENT_NOT_FOUND_MESSAGE = 'No se encontró la compra.';
export const PAYMENT_NOT_PAYABLE_MESSAGE = 'Solo una compra confirmada admite pagos.';
export const PAYMENT_GENERIC_ERROR_MESSAGE = 'Ocurrió un error inesperado. Inténtalo de nuevo.';
export const PAYMENT_VALIDATION_ERROR_MESSAGE = 'Revisa los datos ingresados.';

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

function toError(err: HttpErrorResponse): PaymentApiError {
  if (err.status === 0) return new PaymentApiError(PAYMENT_NETWORK_ERROR_MESSAGE, 0);
  if (err.status === 400) {
    const general = messages((err.error as Record<string, unknown> | null)?.['non_field_errors']);
    return new PaymentApiError(general ?? PAYMENT_VALIDATION_ERROR_MESSAGE, 400, toPaymentFieldErrors(err.error));
  }
  if (err.status === 404) return new PaymentApiError(PAYMENT_NOT_FOUND_MESSAGE, 404);
  if (err.status === 409) {
    const detail = (err.error as { detail?: unknown } | null)?.detail;
    return new PaymentApiError(typeof detail === 'string' ? detail : PAYMENT_NOT_PAYABLE_MESSAGE, 409);
  }
  return new PaymentApiError(PAYMENT_GENERIC_ERROR_MESSAGE, err.status);
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
