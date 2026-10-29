import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import {
  FieldErrors,
  Supplier,
  SupplierApiError,
  SupplierDto,
  SupplierInput,
  SupplierListParams,
} from '../models/supplier';

export const NETWORK_ERROR_MESSAGE = 'No se pudo conectar con el servidor. Inténtalo de nuevo.';
export const NOT_FOUND_MESSAGE = 'Proveedor no encontrado.';
export const GENERIC_ERROR_MESSAGE = 'Ocurrió un error inesperado. Inténtalo de nuevo.';
export const VALIDATION_ERROR_MESSAGE = 'Revisa los datos ingresados.';

/** Campo del formulario -> campo de la API. */
const API_FIELDS: Readonly<Record<keyof SupplierInput, string>> = {
  name: 'name',
  taxId: 'tax_id',
  phone: 'phone',
  email: 'email',
  notes: 'notes',
};
const FORM_FIELDS = Object.keys(API_FIELDS) as (keyof SupplierInput)[];

function toSupplier(dto: SupplierDto): Supplier {
  return {
    id: dto.id,
    name: dto.name,
    taxId: dto.tax_id,
    phone: dto.phone,
    email: dto.email,
    notes: dto.notes,
    active: dto.active,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function toBody(input: Partial<SupplierInput>): Record<string, string> {
  const body: Record<string, string> = {};
  for (const field of FORM_FIELDS) {
    const value = input[field];
    if (value !== undefined) body[API_FIELDS[field]] = value;
  }
  return body;
}

function toFieldErrors(body: unknown): FieldErrors {
  const errors: FieldErrors = {};
  if (body && typeof body === 'object') {
    const record = body as Record<string, unknown>;
    for (const field of FORM_FIELDS) {
      const value = record[API_FIELDS[field]];
      if (Array.isArray(value)) {
        errors[field] = value.map(String);
      }
    }
  }
  return errors;
}

function toApiError(err: HttpErrorResponse): SupplierApiError {
  if (err.status === 0) {
    return new SupplierApiError(NETWORK_ERROR_MESSAGE, 0);
  }
  if (err.status === 400) {
    return new SupplierApiError(VALIDATION_ERROR_MESSAGE, 400, toFieldErrors(err.error));
  }
  if (err.status === 404) {
    return new SupplierApiError(NOT_FOUND_MESSAGE, 404);
  }
  return new SupplierApiError(GENERIC_ERROR_MESSAGE, err.status);
}

@Injectable({
  providedIn: 'root',
})
export class SuppliersApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/suppliers/`;

  list(params: SupplierListParams = {}): Observable<Page<Supplier>> {
    let httpParams = new HttpParams();
    if (params.search) httpParams = httpParams.set('search', params.search);
    if (params.active !== undefined) httpParams = httpParams.set('active', String(params.active));
    if (params.page !== undefined) httpParams = httpParams.set('page', String(params.page));
    if (params.pageSize !== undefined) httpParams = httpParams.set('page_size', String(params.pageSize));
    return this.http.get<Page<SupplierDto>>(this.baseUrl, { params: httpParams }).pipe(
      map((page): Page<Supplier> => ({ ...page, results: page.results.map(toSupplier) })),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err))),
    );
  }

  get(id: string): Observable<Supplier> {
    return this.request(this.http.get<SupplierDto>(`${this.baseUrl}${id}/`));
  }

  create(input: SupplierInput): Observable<Supplier> {
    return this.request(this.http.post<SupplierDto>(this.baseUrl, toBody(input)));
  }

  update(id: string, input: Partial<SupplierInput>): Observable<Supplier> {
    return this.request(this.http.patch<SupplierDto>(`${this.baseUrl}${id}/`, toBody(input)));
  }

  activate(id: string): Observable<Supplier> {
    return this.request(this.http.post<SupplierDto>(`${this.baseUrl}${id}/activate/`, {}));
  }

  deactivate(id: string): Observable<Supplier> {
    return this.request(this.http.post<SupplierDto>(`${this.baseUrl}${id}/deactivate/`, {}));
  }

  private request(source: Observable<SupplierDto>): Observable<Supplier> {
    return source.pipe(
      map(toSupplier),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err))),
    );
  }
}
