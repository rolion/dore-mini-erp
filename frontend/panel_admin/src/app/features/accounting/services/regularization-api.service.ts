import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  RegularizationRequest,
  RegularizationSummary,
  SummaryDto,
  toRegularizationError,
  toSummary,
} from '../models/regularization';

/** Previsualiza y aplica la regularización de pagos históricos (API `/api/accounting/regularization/`). */
@Injectable({ providedIn: 'root' })
export class RegularizationApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/accounting/regularization/`;

  preview(request: RegularizationRequest): Observable<RegularizationSummary> {
    return this.request(this.http.post<SummaryDto>(`${this.baseUrl}preview/`, request));
  }

  /** La confirmación explícita viaja siempre: el servidor rechaza una aplicación sin `confirm`. */
  apply(request: RegularizationRequest): Observable<RegularizationSummary> {
    return this.request(this.http.post<SummaryDto>(`${this.baseUrl}apply/`, { ...request, confirm: true }));
  }

  private request(source: Observable<SummaryDto>): Observable<RegularizationSummary> {
    return source.pipe(
      map(toSummary),
      catchError((err: HttpErrorResponse) => throwError(() => toRegularizationError(err.status, err.error))),
    );
  }
}
