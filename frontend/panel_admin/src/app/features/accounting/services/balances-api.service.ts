import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { BalanceFilters, Balances, BalancesDto, toBalances } from '../models/balances';
import { toJournalError } from '../models/journal';

/** Sumas y saldos por cuenta sobre el libro de asientos (API `/api/accounting/balances/`, solo lectura). */
@Injectable({ providedIn: 'root' })
export class BalancesApiService {
  private http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/accounting/balances/`;

  get(filters: BalanceFilters): Observable<Balances> {
    let params = new HttpParams();
    if (filters.dateFrom) params = params.set('date_from', filters.dateFrom);
    if (filters.dateTo) params = params.set('date_to', filters.dateTo);
    if (filters.accountClass) params = params.set('account_class', filters.accountClass);
    if (filters.accountId) params = params.set('account_id', filters.accountId);
    return this.http.get<BalancesDto>(this.url, { params }).pipe(
      map(toBalances),
      catchError((err: HttpErrorResponse) => throwError(() => toJournalError(err.status, err.error))),
    );
  }
}
