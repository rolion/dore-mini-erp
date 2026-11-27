import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { tr } from '../../../core/i18n/translate';
import { Page } from '../../../shared/models/page';
import { Evaluation } from '../models/odontogram';
import {
  EncounterAction, EncounterDetail, EncounterFailure, EncounterFilters, EncounterList, PatientEncounter,
} from '../models/encounter';

/** Traduce un código estable del servidor; si el catálogo no lo conoce, conserva el mensaje que llegó. */
function byCode(code: unknown, fallback: string): string {
  if (typeof code !== 'string' || !code) return fallback;
  const key = `DENTISTRY.ENCOUNTER.VAL_${code.toUpperCase()}`;
  const text = tr(key);
  return text === key ? fallback : text;
}

export function encounterFailure(error: unknown): EncounterFailure {
  if (!(error instanceof HttpErrorResponse)) return { message: tr('DENTISTRY.ENCOUNTER.ERR_GENERICO'), code: '', status: 0 };
  const body = (error.error ?? {}) as Record<string, unknown>;
  const code = typeof body['code'] === 'string' ? body['code'] : '';
  if (error.status === 409) {
    const detail = typeof body['detail'] === 'string' ? body['detail'] : tr('DENTISTRY.ENCOUNTER.ERR_ESTADO');
    return { message: byCode(code, detail), code, status: 409 };
  }
  if (error.status === 400) {
    const reason = body['reason'];
    const text = Array.isArray(reason) ? String(reason[0] ?? '') : '';
    return { message: text || tr('DENTISTRY.ENCOUNTER.ERR_REVISA'), code, status: 400 };
  }
  if (error.status === 403) return { message: tr('DENTISTRY.ENCOUNTER.ERR_PERMISO'), code, status: 403 };
  if (error.status === 404) return { message: tr('DENTISTRY.ENCOUNTER.ERR_NO_ENCONTRADA'), code, status: 404 };
  return { message: tr('DENTISTRY.ENCOUNTER.ERR_GENERICO'), code, status: error.status };
}

@Injectable({ providedIn: 'root' })
export class EncountersApiService {
  private http = inject(HttpClient);
  private root = `${environment.apiUrl}/dentistry/`;

  list(filters: EncounterFilters): Observable<EncounterList> {
    let params = new HttpParams().set('page', filters.page);
    const optional: [string, string][] = [
      ['from', filters.from], ['to', filters.to], ['professional', filters.professional], ['search', filters.search.trim()],
      ['status', filters.status], ['encounter_status', filters.encounter_status],
    ];
    for (const [key, value] of optional) if (value) params = params.set(key, value);
    return this.http.get<EncounterList>(`${this.root}appointments/`, { params });
  }

  detail(appointmentId: string): Observable<EncounterDetail> {
    return this.http.get<EncounterDetail>(`${this.root}appointments/${appointmentId}/encounter/`);
  }

  act(appointmentId: string, action: EncounterAction, reason = ''): Observable<EncounterDetail> {
    const body = action === 'cancel' ? { reason } : {};
    return this.http.post<EncounterDetail>(`${this.root}appointments/${appointmentId}/encounter/${action}/`, body);
  }

  saveObservations(encounterId: string, observations: string): Observable<EncounterDetail> {
    return this.http.patch<EncounterDetail>(`${this.root}encounters/${encounterId}/`, { observations });
  }

  createOdontogram(encounterId: string): Observable<Evaluation> {
    return this.http.post<Evaluation>(`${this.root}encounters/${encounterId}/odontogram/`, {});
  }

  forPatient(customerId: string): Observable<Page<PatientEncounter>> {
    return this.http.get<Page<PatientEncounter>>(`${this.root}patients/${customerId}/encounters/`,
      { params: new HttpParams().set('page_size', 100) });
  }
}
