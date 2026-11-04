import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { tr } from '../../../core/i18n/translate';
import { Page } from '../../../shared/models/page';
import {
  DentalProforma, DentalProformaFailure, DentalProformaInput, DentalProformaStatus, DentalProformaSummary,
} from '../models/dental-proforma';

function firstMessage(value: unknown): string {
  return Array.isArray(value) ? String(value[0] ?? '') : typeof value === 'string' ? value : '';
}

const FIELD_ERRORS = ['quantity', 'unit_price', 'service_id', 'customer_id', 'valid_until', 'notes', 'lines', 'date', 'id',
  'dental_piece'];

/** Traduce el error de un campo por su nombre; si no se conoce, conserva el mensaje del servidor. */
function fieldMessage(field: string, value: unknown): string {
  return FIELD_ERRORS.includes(field) ? tr(`DENTISTRY.PROFORMAS.E_${field.toUpperCase()}`) : firstMessage(value);
}

export function toFailure(error: unknown): DentalProformaFailure {
  const none = { fields: {}, lines: [], conflict: false };
  if (!(error instanceof HttpErrorResponse)) return { message: tr('DENTISTRY.PROFORMAS.ERR_GENERICO'), ...none };
  const body = (error.error ?? {}) as Record<string, unknown>;
  if (error.status === 409) return { message: tr('DENTISTRY.PROFORMAS.ERR_ESTADO'), ...none, conflict: true };
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
    return { message: tr('DENTISTRY.PROFORMAS.ERR_REVISA'), fields, lines, conflict: false };
  }
  if (error.status === 403) {
    const key = body['code'] === 'module_disabled' ? 'ERR_PERMISO' : 'ERR_PERMISO_PRECIO';
    return { message: tr(`DENTISTRY.PROFORMAS.${key}`), ...none };
  }
  if (error.status === 404) return { message: tr('DENTISTRY.PROFORMAS.ERR_NO_ENCONTRADA'), ...none };
  return { message: tr('DENTISTRY.PROFORMAS.ERR_CONEXION'), ...none };
}

@Injectable({ providedIn: 'root' })
export class DentalProformasApiService {
  private http = inject(HttpClient);
  private readonly root = `${environment.apiUrl}/dentistry/`;

  listForPatient(patientId: string, filters: { status?: DentalProformaStatus | ''; page?: number } = {}):
    Observable<Page<DentalProformaSummary>> {
    let params = new HttpParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== '') params = params.set(key, String(value));
    }
    return this.http.get<Page<DentalProformaSummary>>(`${this.root}patients/${patientId}/proformas/`, { params });
  }

  get(id: string): Observable<DentalProforma> {
    return this.http.get<DentalProforma>(`${this.root}proformas/${id}/`).pipe(this.failures());
  }

  create(patientId: string, input: DentalProformaInput): Observable<DentalProforma> {
    return this.http.post<DentalProforma>(`${this.root}patients/${patientId}/proformas/`, input).pipe(this.failures());
  }

  update(id: string, input: DentalProformaInput): Observable<DentalProforma> {
    return this.http.put<DentalProforma>(`${this.root}proformas/${id}/`, input).pipe(this.failures());
  }

  present(id: string): Observable<DentalProforma> {
    return this.http.post<DentalProforma>(`${this.root}proformas/${id}/present/`, {}).pipe(this.failures());
  }

  newVersion(id: string): Observable<DentalProforma> {
    return this.http.post<DentalProforma>(`${this.root}proformas/${id}/new-version/`, {}).pipe(this.failures());
  }

  private failures<T>() {
    return catchError<T, Observable<never>>(error => throwError(() => toFailure(error)));
  }
}
