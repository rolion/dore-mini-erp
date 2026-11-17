import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  JournalDetailDto,
  JournalEntryDetail,
  JournalFilters,
  JournalInputBody,
  JournalPage,
  JournalPageDto,
  toJournalDetail,
  toJournalError,
  toJournalPage,
} from '../models/journal';

export interface JournalListParams extends Partial<JournalFilters> {
  page?: number;
  pageSize?: number;
}

/** Libro de asientos (API `/api/accounting/journal-entries/`): alta manual y reversión; sin edición ni borrado. */
@Injectable({ providedIn: 'root' })
export class JournalApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/accounting/journal-entries/`;

  list(query: JournalListParams): Observable<JournalPage> {
    let params = new HttpParams();
    const set = (name: string, value: string | number | undefined): void => {
      if (value !== undefined && value !== '') params = params.set(name, String(value));
    };
    set('date_from', query.dateFrom);
    set('date_to', query.dateTo);
    set('account_id', query.accountId);
    set('source', query.source);
    set('page', query.page);
    set('page_size', query.pageSize);
    return this.http.get<JournalPageDto>(this.baseUrl, { params }).pipe(map(toJournalPage), catchError(this.fail));
  }

  get(id: string): Observable<JournalEntryDetail> {
    return this.http.get<JournalDetailDto>(`${this.baseUrl}${id}/`).pipe(map(toJournalDetail), catchError(this.fail));
  }

  create(body: JournalInputBody): Observable<JournalEntryDetail> {
    return this.http.post<JournalDetailDto>(this.baseUrl, body).pipe(map(toJournalDetail), catchError(this.fail));
  }

  reverse(id: string, reversalDate: string, reason: string): Observable<JournalEntryDetail> {
    return this.http
      .post<JournalDetailDto>(`${this.baseUrl}${id}/reverse/`, { reversal_date: reversalDate, reason })
      .pipe(map(toJournalDetail), catchError(this.fail));
  }

  private fail = (err: HttpErrorResponse): Observable<never> => throwError(() => toJournalError(err.status, err.error));
}
