import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  CashFlow,
  CashFlowDto,
  CashFlowFilters,
  CashFlowMovementPage,
  CashFlowMovementPageDto,
  toCashFlow,
  toCashFlowMovementPage,
} from '../models/cash-flow';
import { toJournalError } from '../models/journal';

/** Detalle del flujo de dinero (API `/api/accounting/cash-flow/`, solo lectura). */
@Injectable({ providedIn: 'root' })
export class CashFlowApiService {
  private http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/accounting/cash-flow/`;

  summary(dateFrom: string, dateTo: string): Observable<CashFlow> {
    const params = new HttpParams().set('date_from', dateFrom).set('date_to', dateTo);
    return this.http.get<CashFlowDto>(this.url, { params }).pipe(map(toCashFlow), catchError(this.fail));
  }

  movements(filters: CashFlowFilters, page: number, pageSize: number): Observable<CashFlowMovementPage> {
    let params = new HttpParams().set('date_from', filters.dateFrom).set('date_to', filters.dateTo);
    if (filters.accountId) params = params.set('account_id', filters.accountId);
    if (filters.type) params = params.set('type', filters.type);
    params = params.set('page', String(page)).set('page_size', String(pageSize));
    return this.http
      .get<CashFlowMovementPageDto>(`${this.url}movements/`, { params })
      .pipe(map(toCashFlowMovementPage), catchError(this.fail));
  }

  private fail = (err: HttpErrorResponse): Observable<never> => throwError(() => toJournalError(err.status, err.error));
}
