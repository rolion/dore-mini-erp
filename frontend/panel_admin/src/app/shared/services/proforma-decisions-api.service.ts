import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { tr } from '../../core/i18n/translate';
import { DecisionBody, DecisionFailure, DecisionResult, PrintableProforma } from '../models/proforma-decisions';

/** Prefijo de la API de cada módulo: `quotations/proformas` u `dentistry/proformas`. */
export type ProformaApiBase = 'quotations/proformas' | 'dentistry/proformas';

const KNOWN_FIELDS = ['accepted_by_name', 'medium', 'reference', 'reason', 'line_ids', 'decision', 'idempotency_key'];

export function toDecisionFailure(error: unknown): DecisionFailure {
  const none = { fields: {}, conflict: false };
  if (!(error instanceof HttpErrorResponse)) return { message: tr('PROFORMA_DECISIONS.ERR_GENERICO'), ...none };
  const body = (error.error ?? {}) as Record<string, unknown>;
  if (error.status === 409) return { message: tr('PROFORMA_DECISIONS.ERR_ESTADO'), ...none, conflict: true };
  if (error.status === 400) {
    const fields: Record<string, string> = {};
    for (const key of Object.keys(body)) {
      fields[key] = KNOWN_FIELDS.includes(key) ? tr(`PROFORMA_DECISIONS.E_${key.toUpperCase()}`) : String(body[key]);
    }
    return { message: tr('PROFORMA_DECISIONS.ERR_REVISA'), fields, conflict: false };
  }
  if (error.status === 403) return { message: tr('PROFORMA_DECISIONS.ERR_PERMISO'), ...none };
  if (error.status === 404) return { message: tr('PROFORMA_DECISIONS.ERR_NO_ENCONTRADA'), ...none };
  return { message: tr('PROFORMA_DECISIONS.ERR_CONEXION'), ...none };
}

/** Registra, rectifica e imprime decisiones de proformas; el backend es la autoridad de cada regla. */
@Injectable({ providedIn: 'root' })
export class ProformaDecisionsApiService {
  private http = inject(HttpClient);

  private url(base: ProformaApiBase, id: string, path: string): string {
    return `${environment.apiUrl}/${base}/${id}/${path}`;
  }

  decide(base: ProformaApiBase, id: string, body: DecisionBody): Observable<DecisionResult> {
    return this.http.post<DecisionResult>(this.url(base, id, 'decisions/'), body)
      .pipe(catchError(error => throwError(() => toDecisionFailure(error))));
  }

  rectify(base: ProformaApiBase, id: string, lineId: string, body: DecisionBody): Observable<DecisionResult> {
    return this.http.post<DecisionResult>(this.url(base, id, `lines/${lineId}/rectify/`), body)
      .pipe(catchError(error => throwError(() => toDecisionFailure(error))));
  }

  printable(base: ProformaApiBase, id: string): Observable<PrintableProforma> {
    return this.http.get<PrintableProforma>(this.url(base, id, 'printable/'))
      .pipe(catchError(error => throwError(() => toDecisionFailure(error))));
  }
}
