import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import { toApiError } from '../models/api-error';
import { ListParams, Unit, UnitDto, UnitInput } from '../models/unit';

export function toUnit(dto: UnitDto): Unit {
  return {
    id: dto.id,
    name: dto.name,
    abbreviation: dto.abbreviation,
    allowsFractions: dto.allows_fractions,
    active: dto.active,
    inUse: dto.in_use,
  };
}

function toBody(input: Partial<UnitInput>): Record<string, string | boolean> {
  const body: Record<string, string | boolean> = {};
  if (input.name !== undefined) body['name'] = input.name;
  if (input.abbreviation !== undefined) body['abbreviation'] = input.abbreviation;
  if (input.allowsFractions !== undefined) body['allows_fractions'] = input.allowsFractions;
  return body;
}

@Injectable({
  providedIn: 'root',
})
export class UnitsApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/units/`;

  list(params: ListParams = {}): Observable<Page<Unit>> {
    let httpParams = new HttpParams();
    if (params.search) httpParams = httpParams.set('search', params.search);
    if (params.active !== undefined) httpParams = httpParams.set('active', String(params.active));
    if (params.page !== undefined) httpParams = httpParams.set('page', String(params.page));
    if (params.pageSize !== undefined) httpParams = httpParams.set('page_size', String(params.pageSize));
    return this.http.get<Page<UnitDto>>(this.baseUrl, { params: httpParams }).pipe(
      map((page): Page<Unit> => ({ ...page, results: page.results.map(toUnit) })),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }

  create(input: UnitInput): Observable<Unit> {
    return this.request(this.http.post<UnitDto>(this.baseUrl, toBody(input)));
  }

  update(id: string, input: Partial<UnitInput>): Observable<Unit> {
    return this.request(this.http.patch<UnitDto>(`${this.baseUrl}${id}/`, toBody(input)));
  }

  activate(id: string): Observable<Unit> {
    return this.request(this.http.post<UnitDto>(`${this.baseUrl}${id}/activate/`, {}));
  }

  deactivate(id: string): Observable<Unit> {
    return this.request(this.http.post<UnitDto>(`${this.baseUrl}${id}/deactivate/`, {}));
  }

  private request(source: Observable<UnitDto>): Observable<Unit> {
    return source.pipe(
      map(toUnit),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }
}
