import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { toApiError } from '../models/accounting';
import {
  CategoryRow,
  CategoryRowDto,
  PostingConfig,
  PostingConfigDto,
  PostingModule,
  RoleRow,
  RoleRowDto,
  toCategoryRow,
  toPostingConfig,
  toRoleRow,
} from '../models/posting-config';

/** Configuración de asientos automáticos por módulo (API `/api/accounting/posting-config/`). El método de pago → cuenta se edita con `AccountingApiService.configureMethod`. */
@Injectable({ providedIn: 'root' })
export class PostingConfigApiService {
  private http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/accounting/posting-config/`;

  get(module: PostingModule): Observable<PostingConfig> {
    const params = new HttpParams().set('module', module);
    return this.request(this.http.get<PostingConfigDto>(this.url, { params }), toPostingConfig);
  }

  setRoleAccount(role: string, accountId: string | null): Observable<RoleRow> {
    return this.request(this.http.put<RoleRowDto>(`${this.url}roles/${role}/`, { account_id: accountId }), toRoleRow);
  }

  setCategoryAccount(categoryId: string, accountId: string | null): Observable<CategoryRow> {
    return this.request(
      this.http.put<CategoryRowDto>(`${this.url}categories/${categoryId}/`, { account_id: accountId }),
      toCategoryRow,
    );
  }

  private request<D, T>(source: Observable<D>, convert: (dto: D) => T): Observable<T> {
    return source.pipe(
      map(convert),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }
}
