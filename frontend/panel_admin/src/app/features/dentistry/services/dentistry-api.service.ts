import { tr } from '../../../core/i18n/translate';
import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import { ClinicalInput, Demographics, Patient, PatientHistory, PatientSummary } from '../models/patient';

export function errorMessage(error: HttpErrorResponse): string {
  const detail: unknown = error.error?.detail;
  if (typeof detail === 'string') return detail;
  if (error.status === 400) return tr('DENTISTRY.DENTISTRY_API_SERVICE.REVISA_LOS_CAMPOS_SENALADOS');
  if (error.status === 403) return tr('DENTISTRY.DENTISTRY_API_SERVICE.NO_TIENES_PERMISO_PARA_ACCEDER');
  if (error.status === 404) return tr('DENTISTRY.DENTISTRY_API_SERVICE.NO_SE_ENCONTRO_EL_PACIENTE');
  return tr('SETTINGS.SETTING.NO_SE_PUDO_COMPLETAR_LA');
}
export function fieldErrors(error: HttpErrorResponse): Record<string, string> {
  const result: Record<string, string> = {};
  if (error.error && typeof error.error === 'object') {
    for (const [key, value] of Object.entries(error.error as Record<string, unknown>)) {
      if (Array.isArray(value)) result[key] = value.map(String).join(' ');
    }
  }
  return result;
}

@Injectable({ providedIn: 'root' })
export class DentistryApiService {
  private http = inject(HttpClient);
  private root = `${environment.apiUrl}/dentistry/`;
  private patients = `${this.root}patients/`;
  capabilities() { return this.http.get<{ clinical_access: boolean }>(`${this.root}capabilities/`); }
  list(search: string, active: string, page: number) {
    return this.http.get<Page<PatientSummary>>(this.patients, {
      params: new HttpParams().set('search', search).set('active', active).set('page', page),
    });
  }
  get(id: string) { return this.http.get<Patient>(`${this.patients}${id}/`); }
  create(customerId: string) { return this.http.post<Patient>(this.patients, { customer_id: customerId }); }
  update(id: string, input: ClinicalInput) { return this.http.patch<Patient>(`${this.patients}${id}/`, input); }
  setActive(id: string, active: boolean) {
    return this.http.post<Patient>(`${this.patients}${id}/${active ? 'activate' : 'archive'}/`, {});
  }
  demographics(id: string, input: Demographics) {
    return this.http.patch<Demographics>(`${environment.apiUrl}/customers/${id}/demographics/`, input);
  }
  history(id: string, clinical: boolean, page: number) {
    const url = clinical ? `${this.patients}${id}/history/`
      : `${environment.apiUrl}/customers/${id}/demographics/history/`;
    return this.http.get<Page<PatientHistory>>(url, { params: new HttpParams().set('page', page) });
  }
}
