import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { toApiError } from '../models/accounting';
import { FiscalPeriod, FiscalPeriodDto, FiscalPeriodInput, toFiscalPeriod } from '../models/fiscal-period';

/** Períodos fiscales de la empresa (API `/api/accounting/fiscal-periods/`). */
@Injectable({ providedIn: 'root' })
export class FiscalPeriodsApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/accounting/fiscal-periods/`;

  list(): Observable<FiscalPeriod[]> {
    return this.request(this.http.get<FiscalPeriodDto[]>(this.baseUrl), (rows) => rows.map(toFiscalPeriod));
  }

  create(input: FiscalPeriodInput): Observable<FiscalPeriod> {
    return this.request(this.http.post<FiscalPeriodDto>(this.baseUrl, toBody(input)), toFiscalPeriod);
  }

  update(id: string, input: FiscalPeriodInput): Observable<FiscalPeriod> {
    return this.request(this.http.patch<FiscalPeriodDto>(`${this.baseUrl}${id}/`, toBody(input)), toFiscalPeriod);
  }

  close(id: string): Observable<FiscalPeriod> {
    return this.request(this.http.post<FiscalPeriodDto>(`${this.baseUrl}${id}/close/`, {}), toFiscalPeriod);
  }

  reopen(id: string): Observable<FiscalPeriod> {
    return this.request(this.http.post<FiscalPeriodDto>(`${this.baseUrl}${id}/reopen/`, {}), toFiscalPeriod);
  }

  private request<D, T>(source: Observable<D>, convert: (dto: D) => T): Observable<T> {
    return source.pipe(
      map(convert),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }
}

function toBody(input: FiscalPeriodInput): { name: string; start_date: string; end_date: string } {
  return { name: input.name, start_date: input.startDate, end_date: input.endDate };
}
