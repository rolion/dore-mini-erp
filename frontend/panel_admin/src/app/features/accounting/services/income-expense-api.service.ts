import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { IncomeExpenseFilters, IncomeExpenseReport, IncomeExpenseReportDto, toIncomeExpenseReport } from '../models/income-expense';
import { toJournalError } from '../models/journal';

/** Ingresos y egresos por mes (API `/api/accounting/income-expense/`, solo lectura). */
@Injectable({ providedIn: 'root' })
export class IncomeExpenseApiService {
  private http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/accounting/income-expense/`;

  get(filters: IncomeExpenseFilters): Observable<IncomeExpenseReport> {
    let params = new HttpParams();
    if (filters.periodId) params = params.set('period_id', filters.periodId);
    if (filters.months.length > 0) params = params.set('months', filters.months.join(','));
    return this.http.get<IncomeExpenseReportDto>(this.url, { params }).pipe(
      map(toIncomeExpenseReport),
      catchError((err: HttpErrorResponse) => throwError(() => toJournalError(err.status, err.error))),
    );
  }
}
