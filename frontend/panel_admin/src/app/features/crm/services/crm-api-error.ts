import { HttpErrorResponse } from '@angular/common/http';
import { Observable, OperatorFunction, catchError, throwError } from 'rxjs';
import { CrmApiError, CrmFieldErrors, genericErrorMessage, networkErrorMessage } from '../models/board';
import { CrmContact } from '../models/lead';

const camel = (key: string): string => key.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());

function messages(value: unknown): string | undefined {
  if (typeof value === 'string') return value;
  return Array.isArray(value) && value.length ? value.map(String).join(' ') : undefined;
}

function isContact(value: unknown): value is CrmContact {
  return !!value && typeof value === 'object' && typeof (value as CrmContact).id === 'string';
}

/**
 * Traduce un error HTTP de prospectos y oportunidades: 400 → mensajes por campo (`{campo: [mensajes]}`, con
 * `non_field_errors`/`detail` como mensaje general), 409 → `{detail, code, candidates?}`, 0 → sin conexión.
 */
export function toCrmApiError(error: HttpErrorResponse): CrmApiError {
  if (error.status === 0) {
    return new CrmApiError(networkErrorMessage(), 0);
  }
  const body = (error.error && typeof error.error === 'object' ? error.error : {}) as Record<string, unknown>;
  const detail = messages(body['detail']) ?? '';
  const code = typeof body['code'] === 'string' ? body['code'] : null;
  if (error.status === 400) {
    const fieldErrors: CrmFieldErrors = {};
    for (const [key, value] of Object.entries(body)) {
      if (key === 'detail' || key === 'code' || key === 'non_field_errors') continue;
      const text = messages(value);
      if (text) fieldErrors[camel(key)] = text;
    }
    const general = messages(body['non_field_errors']) ?? detail;
    return new CrmApiError(general || genericErrorMessage(), 400, fieldErrors, code);
  }
  const candidates = Array.isArray(body['candidates']) ? body['candidates'].filter(isContact) : [];
  return new CrmApiError(detail || genericErrorMessage(), error.status, {}, code, 0, candidates);
}

/** Operador que convierte cualquier error HTTP en `CrmApiError`. */
export function crmErrors<T>(): OperatorFunction<T, T> {
  return (source: Observable<T>) =>
    source.pipe(catchError((err: HttpErrorResponse) => throwError(() => toCrmApiError(err))));
}
