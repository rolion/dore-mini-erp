import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { BalanceSheet, BalanceSheetDto, BalanceSheetFilters, toBalanceSheet } from '../models/balance-sheet';
import { toJournalError } from '../models/journal';

/** Balance general sobre el libro de asientos (API `/api/accounting/balance-sheet/`, solo lectura). */
@Injectable({ providedIn: 'root' })
export class BalanceSheetApiService {
  private http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/accounting/balance-sheet/`;

  get(filters: BalanceSheetFilters): Observable<BalanceSheet> {
    let params = new HttpParams();
    if (filters.dateFrom) params = params.set('date_from', filters.dateFrom);
    if (filters.dateTo) params = params.set('date_to', filters.dateTo);
    return this.http.get<BalanceSheetDto>(this.url, { params }).pipe(
      map(toBalanceSheet),
      catchError((err: HttpErrorResponse) => throwError(() => toJournalError(err.status, err.error))),
    );
  }
}
