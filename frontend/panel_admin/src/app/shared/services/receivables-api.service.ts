import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { tr } from '../../core/i18n/translate';
import { Page } from '../models/page';
import {
  Commitment, ObligationFilters, ObligationSummary, PaymentInput, PaymentRegistered, ReceivableFailure, SourceKind,
} from '../models/receivable';

const FIELD_ERRORS = ['amount', 'payment_method', 'payment_date', 'reference', 'allocations'];

export function toFailure(error: unknown): ReceivableFailure {
  const none = { fields: {}, conflict: false };
  if (!(error instanceof HttpErrorResponse)) return { message: tr('RECEIVABLES.ERR_GENERICO'), ...none };
  const body = (error.error ?? {}) as Record<string, unknown>;
  if (error.status === 409) return { message: tr('RECEIVABLES.ERR_ESTADO'), ...none, conflict: true };
  if (error.status === 400) {
    const fields: Record<string, string> = {};
    for (const key of Object.keys(body)) {
      if (FIELD_ERRORS.includes(key)) fields[key] = tr(`RECEIVABLES.E_${key.toUpperCase()}`);
    }
    return { message: tr('RECEIVABLES.ERR_REVISA'), fields, conflict: false };
  }
  if (error.status === 403) return { message: tr('RECEIVABLES.ERR_PERMISO'), ...none };
  if (error.status === 404) return { message: tr('RECEIVABLES.ERR_NO_ENCONTRADO'), ...none };
  return { message: tr('RECEIVABLES.ERR_CONEXION'), ...none };
}

@Injectable({ providedIn: 'root' })
export class ReceivablesApiService {
  private http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/receivables/`;

  list(filters: ObligationFilters = {}): Observable<Page<ObligationSummary>> {
    let params = new HttpParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== '') params = params.set(key, String(value));
    }
    return this.http.get<Page<ObligationSummary>>(`${this.base}obligations/`, { params });
  }

  get(kind: SourceKind, number: string): Observable<Commitment> {
    return this.http
      .get<Commitment>(`${this.base}commitments/${kind}/${encodeURIComponent(number)}/`)
      .pipe(catchError((error) => throwError(() => toFailure(error))));
  }

  pay(kind: SourceKind, number: string, input: PaymentInput): Observable<PaymentRegistered> {
    return this.http
      .post<PaymentRegistered>(`${this.base}commitments/${kind}/${encodeURIComponent(number)}/payments/`, input)
      .pipe(catchError((error) => throwError(() => toFailure(error))));
  }
}
