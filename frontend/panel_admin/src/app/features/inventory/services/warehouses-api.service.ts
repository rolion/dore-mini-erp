import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import { toApiError } from '../models/api-error';
import { ListParams } from '../models/unit';
import { Warehouse, WarehouseDto, WarehouseInput } from '../models/warehouse';

export function toWarehouse(dto: WarehouseDto): Warehouse {
  return {
    id: dto.id,
    name: dto.name,
    description: dto.description,
    active: dto.active,
    isDefault: dto.is_default,
  };
}

function toBody(input: Partial<WarehouseInput>): Record<string, string | boolean> {
  const body: Record<string, string | boolean> = {};
  if (input.name !== undefined) body['name'] = input.name;
  if (input.description !== undefined) body['description'] = input.description;
  if (input.isDefault !== undefined) body['is_default'] = input.isDefault;
  return body;
}

@Injectable({
  providedIn: 'root',
})
export class WarehousesApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/warehouses/`;

  list(params: ListParams = {}): Observable<Page<Warehouse>> {
    let httpParams = new HttpParams();
    if (params.search) httpParams = httpParams.set('search', params.search);
    if (params.active !== undefined) httpParams = httpParams.set('active', String(params.active));
    if (params.page !== undefined) httpParams = httpParams.set('page', String(params.page));
    if (params.pageSize !== undefined) httpParams = httpParams.set('page_size', String(params.pageSize));
    return this.http.get<Page<WarehouseDto>>(this.baseUrl, { params: httpParams }).pipe(
      map((page): Page<Warehouse> => ({ ...page, results: page.results.map(toWarehouse) })),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }

  create(input: WarehouseInput): Observable<Warehouse> {
    return this.request(this.http.post<WarehouseDto>(this.baseUrl, toBody(input)));
  }

  update(id: string, input: Partial<WarehouseInput>): Observable<Warehouse> {
    return this.request(this.http.patch<WarehouseDto>(`${this.baseUrl}${id}/`, toBody(input)));
  }

  activate(id: string): Observable<Warehouse> {
    return this.request(this.http.post<WarehouseDto>(`${this.baseUrl}${id}/activate/`, {}));
  }

  deactivate(id: string): Observable<Warehouse> {
    return this.request(this.http.post<WarehouseDto>(`${this.baseUrl}${id}/deactivate/`, {}));
  }

  makeDefault(id: string): Observable<Warehouse> {
    return this.request(this.http.post<WarehouseDto>(`${this.baseUrl}${id}/make-default/`, {}));
  }

  private request(source: Observable<WarehouseDto>): Observable<Warehouse> {
    return source.pipe(
      map(toWarehouse),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err.status, err.error))),
    );
  }
}
