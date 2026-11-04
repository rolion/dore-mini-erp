import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { tr } from '../../../core/i18n/translate';
import { Page } from '../../../shared/models/page';
import {
  Appointment, AppointmentAction, AppointmentFailure, AppointmentFilters, AppointmentInput, FreeSlots,
} from '../models/appointment';

/** Bolivia no tiene horario de verano: el desfase es fijo. */
export const BOLIVIA_OFFSET = '-04:00';

export function toServerDateTime(local: string): string {
  return `${local.length === 16 ? `${local}:00` : local}${BOLIVIA_OFFSET}`;
}

export function toLocalInput(iso: string): string {
  return iso.slice(0, 16);
}

export function formatDateTime(iso: string): string {
  const [year, month, day] = iso.slice(0, 10).split('-');
  return `${day}/${month}/${year} ${iso.slice(11, 16)}`;
}

function firstMessage(value: unknown): string {
  return Array.isArray(value) ? String(value[0] ?? '') : typeof value === 'string' ? value : '';
}

export function toFailure(error: unknown): AppointmentFailure {
  if (!(error instanceof HttpErrorResponse)) {
    return { message: tr('AGENDA.CITAS.ERR_GENERICO'), fields: {}, conflict: false };
  }
  const body = (error.error ?? {}) as Record<string, unknown>;
  if (error.status === 409) {
    return { message: firstMessage(body['detail']) || tr('AGENDA.CITAS.ERR_HORARIO'), fields: {}, conflict: true };
  }
  if (error.status === 400) {
    const fields: Record<string, string> = {};
    for (const [key, value] of Object.entries(body)) fields[key] = firstMessage(value);
    return { message: tr('AGENDA.CITAS.ERR_REVISA'), fields, conflict: false };
  }
  if (error.status === 403) {
    return { message: tr('AGENDA.CITAS.ERR_PERMISO'), fields: {}, conflict: false };
  }
  if (error.status === 404) return { message: tr('AGENDA.CITAS.ERR_NO_ENCONTRADA'), fields: {}, conflict: false };
  return { message: tr('AGENDA.CITAS.ERR_CONEXION'), fields: {}, conflict: false };
}

@Injectable({ providedIn: 'root' })
export class AppointmentsApiService {
  private http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/agenda/appointments/`;

  list(filters: AppointmentFilters = {}): Observable<Page<Appointment>> {
    let params = new HttpParams();
    for (const [key, value] of Object.entries(filters)) {
      if (value !== undefined && value !== '') params = params.set(key, String(value));
    }
    return this.http.get<Page<Appointment>>(this.base, { params });
  }

  get(id: string): Observable<Appointment> {
    return this.http.get<Appointment>(`${this.base}${id}/`);
  }

  create(input: AppointmentInput): Observable<Appointment> {
    return this.http.post<Appointment>(this.base, input).pipe(catchError(error => throwError(() => toFailure(error))));
  }

  updateNotes(id: string, notes: string): Observable<Appointment> {
    return this.http.patch<Appointment>(`${this.base}${id}/`, { notes }).pipe(
      catchError(error => throwError(() => toFailure(error))));
  }

  act(id: string, action: AppointmentAction, body: Record<string, unknown> = {}): Observable<Appointment> {
    return this.http.post<Appointment>(`${this.base}${id}/${action.replace('_', '-')}/`, body).pipe(
      catchError(error => throwError(() => toFailure(error))));
  }

  freeSlots(professional: string, dateFrom: string, dateTo: string, duration?: number): Observable<FreeSlots> {
    let params = new HttpParams().set('professional', professional).set('date_from', dateFrom).set('date_to', dateTo);
    if (duration) params = params.set('duration', String(duration));
    return this.http.get<FreeSlots>(`${this.base}free-slots/`, { params });
  }
}
