import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { toApiError } from '../models/accounting';
import { Entry, EntryDto, EntryListFilters, EntryPage, EntryPageDto, toEntry, toEntryPage } from '../models/entry';

export interface EntryListParams extends Partial<EntryListFilters> {
  page?: number;
  pageSize?: number;
}

/** Libro de entradas (API `/api/accounting/entries/`): solo lectura. */
@Injectable({ providedIn: 'root' })
export class EntriesApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/accounting/entries/`;

  list(query: EntryListParams): Observable<EntryPage> {
    let params = new HttpParams();
    const set = (name: string, value: string | number | undefined): void => {
      if (value !== undefined && value !== '') params = params.set(name, String(value));
    };
    set('date_from', query.dateFrom);
    set('date_to', query.dateTo);
    set('account_id', query.accountId);
    set('method', query.method);
    set('origin', query.origin);
    set('page', query.page);
    set('page_size', query.pageSize);
    return this.http.get<EntryPageDto>(this.baseUrl, { params }).pipe(map(toEntryPage), catchError(this.fail));
  }

  get(id: string): Observable<Entry> {
    return this.http.get<EntryDto>(`${this.baseUrl}${id}/`).pipe(map(toEntry), catchError(this.fail));
  }

  private fail = (err: HttpErrorResponse): Observable<never> => throwError(() => toApiError(err.status, err.error));
}
