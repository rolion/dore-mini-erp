import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import { CatalogService, ServiceApiError, ServiceDto, ServiceInput } from '../models/service';

const fields: Record<keyof ServiceInput, string> = {
  name: 'name', code: 'code', description: 'description', basePrice: 'base_price',
  durationMinutes: 'duration_minutes', specialtyId: 'specialty_id',
};

function fromDto(dto: ServiceDto): CatalogService {
  return { id: dto.id, name: dto.name, code: dto.code, description: dto.description,
    basePrice: dto.base_price, durationMinutes: dto.duration_minutes, specialtyId: dto.specialty_id,
    specialtyName: dto.specialty_name, active: dto.active, createdAt: dto.created_at, updatedAt: dto.updated_at };
}

function toBody(input: Partial<ServiceInput>): Record<string, string | number | null> {
  const body: Record<string, string | number | null> = {};
  for (const key of Object.keys(fields) as (keyof ServiceInput)[]) {
    const value = input[key];
    if (value !== undefined) body[fields[key]] = key === 'code' && typeof value === 'string'
      ? value.trim().toUpperCase() : value;
  }
  return body;
}

function apiError(error: HttpErrorResponse): Observable<never> {
  const fieldErrors: Partial<Record<keyof ServiceInput, string>> = {};
  const body: unknown = error.error;
  if (body && typeof body === 'object') {
    const record = body as Record<string, unknown>;
    for (const key of Object.keys(fields) as (keyof ServiceInput)[]) {
      const value = record[fields[key]];
      if (Array.isArray(value)) fieldErrors[key] = value.map(String).join(' ');
    }
  }
  const message = error.status === 0 ? 'No se pudo conectar con el servidor. Inténtalo de nuevo.'
    : error.status === 400 ? 'Revisa los datos ingresados.'
    : error.status === 403 ? 'No tienes permiso para acceder a Servicios.'
    : error.status === 404 ? 'Servicio no encontrado.' : 'No se pudo completar la operación. Inténtalo de nuevo.';
  return throwError(() => new ServiceApiError(message, error.status, fieldErrors));
}

@Injectable({ providedIn: 'root' })
export class ServicesApiService {
  private http = inject(HttpClient);
  private url = `${environment.apiUrl}/services/`;

  list(params: { search?: string; active?: boolean; specialtyId?: string; page?: number; pageSize?: number } = {}): Observable<Page<CatalogService>> {
    let query = new HttpParams();
    if (params.search) query = query.set('search', params.search);
    if (params.active !== undefined) query = query.set('active', params.active);
    if (params.specialtyId) query = query.set('specialty_id', params.specialtyId);
    if (params.page) query = query.set('page', params.page);
    if (params.pageSize) query = query.set('page_size', params.pageSize);
    return this.http.get<Page<ServiceDto>>(this.url, { params: query }).pipe(
      map(page => ({ ...page, results: page.results.map(fromDto) })), catchError(apiError));
  }

  get(id: string): Observable<CatalogService> {
    return this.request(this.http.get<ServiceDto>(`${this.url}${id}/`));
  }
  create(input: ServiceInput): Observable<CatalogService> {
    return this.request(this.http.post<ServiceDto>(this.url, toBody(input)));
  }
  update(id: string, input: Partial<ServiceInput>): Observable<CatalogService> {
    return this.request(this.http.patch<ServiceDto>(`${this.url}${id}/`, toBody(input)));
  }
  setActive(id: string, active: boolean): Observable<CatalogService> {
    return this.request(this.http.post<ServiceDto>(`${this.url}${id}/${active ? 'activate' : 'deactivate'}/`, {}));
  }
  private request(source: Observable<ServiceDto>): Observable<CatalogService> {
    return source.pipe(map(fromDto), catchError(apiError));
  }
}

@Injectable({ providedIn: 'root' })
export class ServiceFiltersState {
  search = '';
  status = 'active';
  pageIndex = 0;
}
