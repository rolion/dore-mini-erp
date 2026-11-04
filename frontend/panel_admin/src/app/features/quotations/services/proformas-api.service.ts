import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';
import { tr } from '../../../core/i18n/translate';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import { Proforma, ProformaFailure, ProformaFilters, ProformaInput, ProformaSummary } from '../models/proforma';

function firstMessage(value: unknown): string {
  return Array.isArray(value) ? String(value[0] ?? '') : typeof value === 'string' ? value : '';
}

const FIELD_ERRORS = ['quantity', 'unit_price', 'service_id', 'customer_id', 'valid_until', 'notes', 'lines', 'date', 'id'];

/** Traduce el error de un campo por su nombre; si no se conoce, conserva el mensaje del servidor. */
function fieldMessage(field: string, value: unknown): string {
  return FIELD_ERRORS.includes(field) ? tr(`QUOTATIONS.PROFORMAS.E_${field.toUpperCase()}`) : firstMessage(value);
}

export function toFailure(error: unknown): ProformaFailure {
  const none = { fields: {}, lines: [], conflict: false };
  if (!(error instanceof HttpErrorResponse)) return { message: tr('QUOTATIONS.PROFORMAS.ERR_GENERICO'), ...none };
  const body = (error.error ?? {}) as Record<string, unknown>;
  if (error.status === 409) return { message: tr('QUOTATIONS.PROFORMAS.ERR_ESTADO'), ...none, conflict: true };
  if (error.status === 400) {
    const fields: Record<string, string> = {};
    let lines: Record<string, string>[] = [];
    for (const [key, value] of Object.entries(body)) {
      if (key === 'lines' && Array.isArray(value) && value.some(item => typeof item === 'object' && item !== null && !Array.isArray(item))) {
        lines = (value as Record<string, unknown>[]).map(item => {
          const row: Record<string, string> = {};
          for (const [field, message] of Object.entries(item ?? {})) row[field] = fieldMessage(field, message);
          return row;
        });
      } else fields[key] = fieldMessage(key, value);
    }
    return { message: tr('QUOTATIONS.PROFORMAS.ERR_REVISA'), fields, lines, conflict: false };
  }
  if (error.status === 403) {
    const key = body['code'] === 'module_disabled' ? 'ERR_PERMISO' : 'ERR_PERMISO_PRECIO';
    return { message: tr(`QUOTATIONS.PROFORMAS.${key}`), ...none };
  }
  if (error.status === 404) return { message: tr('QUOTATIONS.PROFORMAS.ERR_NO_ENCONTRADA'), ...none };
  return { message: tr('QUOTATIONS.PROFORMAS.ERR_CONEXION'), ...none };
}

@Injectable({ providedIn: 'root' })
export class ProformasApiService {
  private http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/quotations/proformas/`;

  list(filters: ProformaFilters = {}): Observable<Page<ProformaSummary>> {
    let params = new HttpParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== '') params = params.set(key, String(value));
    }
    return this.http.get<Page<ProformaSummary>>(this.base, { params });
  }

  get(id: string): Observable<Proforma> {
    return this.http.get<Proforma>(`${this.base}${id}/`).pipe(catchError(error => throwError(() => toFailure(error))));
  }

  create(input: ProformaInput): Observable<Proforma> {
    return this.http.post<Proforma>(this.base, input).pipe(catchError(error => throwError(() => toFailure(error))));
  }

  update(id: string, input: ProformaInput): Observable<Proforma> {
    return this.http.put<Proforma>(`${this.base}${id}/`, input).pipe(catchError(error => throwError(() => toFailure(error))));
  }

  present(id: string): Observable<Proforma> {
    return this.http.post<Proforma>(`${this.base}${id}/present/`, {}).pipe(catchError(error => throwError(() => toFailure(error))));
  }

  newVersion(id: string): Observable<Proforma> {
    return this.http.post<Proforma>(`${this.base}${id}/new-version/`, {}).pipe(catchError(error => throwError(() => toFailure(error))));
  }
}
