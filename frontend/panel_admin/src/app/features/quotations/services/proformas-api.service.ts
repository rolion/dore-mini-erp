import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import { Proforma, ProformaFailure, ProformaFilters, ProformaInput, ProformaSummary } from '../models/proforma';

function firstMessage(value: unknown): string {
  return Array.isArray(value) ? String(value[0] ?? '') : typeof value === 'string' ? value : '';
}

export function toFailure(error: unknown): ProformaFailure {
  const none = { fields: {}, lines: [], conflict: false };
  if (!(error instanceof HttpErrorResponse)) return { message: 'No se pudo completar la operación.', ...none };
  const body = (error.error ?? {}) as Record<string, unknown>;
  if (error.status === 409) {
    return { message: firstMessage(body['detail']) || 'La operación no es válida para el estado actual.', ...none, conflict: true };
  }
  if (error.status === 400) {
    const fields: Record<string, string> = {};
    let lines: Record<string, string>[] = [];
    for (const [key, value] of Object.entries(body)) {
      if (key === 'lines' && Array.isArray(value) && value.some(item => typeof item === 'object' && item !== null && !Array.isArray(item))) {
        lines = (value as Record<string, unknown>[]).map(item => {
          const row: Record<string, string> = {};
          for (const [field, message] of Object.entries(item ?? {})) row[field] = firstMessage(message);
          return row;
        });
      } else fields[key] = firstMessage(value);
    }
    return { message: 'Revisa los datos marcados.', fields, lines, conflict: false };
  }
  if (error.status === 403) {
    const detail = firstMessage(body['detail']);
    return { message: detail || 'No tienes permiso o un módulo requerido no está habilitado.', ...none };
  }
  if (error.status === 404) return { message: 'Proforma no encontrada.', ...none };
  return { message: 'No se pudo conectar con el servidor. Inténtalo de nuevo.', ...none };
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
