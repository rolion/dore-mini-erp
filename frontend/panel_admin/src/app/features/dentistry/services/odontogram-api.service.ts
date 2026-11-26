import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { tr } from '../../../core/i18n/translate';
import { Page } from '../../../shared/models/page';
import { Evaluation, EvaluationInput, OdontogramCatalog } from '../models/odontogram';
import { flattenErrors } from './odontogram-utils';

/** Mensaje para el usuario ante un error de la API de evaluaciones; el 400 añade el detalle por campo. */
export function evaluationError(error: unknown): string {
  if (!(error instanceof HttpErrorResponse)) return tr('DENTISTRY.ODONTOGRAM.ERR_GENERIC');
  const detail: unknown = error.error?.detail;
  if (typeof detail === 'string') return detail;
  if (error.status === 400) {
    const lines = flattenErrors(error.error);
    return lines.length ? `${tr('DENTISTRY.ODONTOGRAM.ERR_REVISA')} ${lines.join(' ')}` : tr('DENTISTRY.ODONTOGRAM.ERR_REVISA');
  }
  if (error.status === 403) return tr('DENTISTRY.ODONTOGRAM.ERR_403');
  if (error.status === 404) return tr('DENTISTRY.ODONTOGRAM.ERR_404');
  if (error.status === 409) return tr('DENTISTRY.ODONTOGRAM.ERR_409');
  return tr('DENTISTRY.ODONTOGRAM.ERR_GENERIC');
}

@Injectable({ providedIn: 'root' })
export class OdontogramApiService {
  private http = inject(HttpClient);
  private root = `${environment.apiUrl}/dentistry/`;

  catalog(): Observable<OdontogramCatalog> {
    return this.http.get<OdontogramCatalog>(`${this.root}odontogram/catalog/`);
  }
  list(customerId: string): Observable<Page<Evaluation>> {
    return this.http.get<Page<Evaluation>>(`${this.root}patients/${customerId}/evaluations/`,
      { params: new HttpParams().set('page_size', 100) });
  }
  get(id: string): Observable<Evaluation> {
    return this.http.get<Evaluation>(`${this.root}evaluations/${id}/`);
  }
  create(customerId: string, input: EvaluationInput): Observable<Evaluation> {
    return this.http.post<Evaluation>(`${this.root}patients/${customerId}/evaluations/`, input);
  }
  update(id: string, input: EvaluationInput): Observable<Evaluation> {
    return this.http.put<Evaluation>(`${this.root}evaluations/${id}/`, input);
  }
  discard(id: string): Observable<void> {
    return this.http.delete<void>(`${this.root}evaluations/${id}/`);
  }
  confirm(id: string): Observable<Evaluation> {
    return this.http.post<Evaluation>(`${this.root}evaluations/${id}/confirm/`, {});
  }
  amend(id: string, reason: string): Observable<Evaluation> {
    return this.http.post<Evaluation>(`${this.root}evaluations/${id}/amend/`, { reason });
  }
}
