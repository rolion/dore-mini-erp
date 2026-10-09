import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import { toApiError } from '../models/api-error';
import { CategoryListParams, ExpenseCategory, ExpenseCategoryDto } from '../models/category';

export function toCategory(dto: ExpenseCategoryDto): ExpenseCategory {
  return { id: dto.id, name: dto.name, active: dto.active, createdAt: dto.created_at, updatedAt: dto.updated_at };
}

@Injectable({
  providedIn: 'root',
})
export class CategoriesApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/expense-categories/`;

  list(params: CategoryListParams = {}): Observable<Page<ExpenseCategory>> {
    let httpParams = new HttpParams();
    if (params.active !== undefined) httpParams = httpParams.set('active', String(params.active));
    if (params.search) httpParams = httpParams.set('search', params.search);
    if (params.page !== undefined) httpParams = httpParams.set('page', String(params.page));
    if (params.pageSize !== undefined) httpParams = httpParams.set('page_size', String(params.pageSize));
    return this.http.get<Page<ExpenseCategoryDto>>(this.baseUrl, { params: httpParams }).pipe(
      map((page): Page<ExpenseCategory> => ({ ...page, results: page.results.map(toCategory) })),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }

  create(name: string): Observable<ExpenseCategory> {
    return this.request(this.http.post<ExpenseCategoryDto>(this.baseUrl, { name }));
  }

  rename(id: string, name: string): Observable<ExpenseCategory> {
    return this.request(this.http.patch<ExpenseCategoryDto>(`${this.baseUrl}${id}/`, { name }));
  }

  activate(id: string): Observable<ExpenseCategory> {
    return this.request(this.http.post<ExpenseCategoryDto>(`${this.baseUrl}${id}/activate/`, {}));
  }

  deactivate(id: string): Observable<ExpenseCategory> {
    return this.request(this.http.post<ExpenseCategoryDto>(`${this.baseUrl}${id}/deactivate/`, {}));
  }

  private request(source: Observable<ExpenseCategoryDto>): Observable<ExpenseCategory> {
    return source.pipe(
      map(toCategory),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }
}
