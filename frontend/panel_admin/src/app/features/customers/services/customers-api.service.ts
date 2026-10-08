import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  Customer,
  CustomerApiError,
  CustomerDto,
  CustomerInput,
  CustomerListParams,
  DuplicateCustomerError,
  DuplicateMatch,
  FieldErrors,
  Page,
} from '../models/customer';

export const NETWORK_ERROR_MESSAGE = 'No se pudo conectar con el servidor. Inténtalo de nuevo.';
export const NOT_FOUND_MESSAGE = 'Cliente no encontrado.';
export const GENERIC_ERROR_MESSAGE = 'Ocurrió un error inesperado. Inténtalo de nuevo.';
export const VALIDATION_ERROR_MESSAGE = 'Revisa los datos ingresados.';
export const DUPLICATE_PHONE_MESSAGE = 'Ya existe un cliente con este teléfono.';

const DUPLICATE_PHONE_CODE = 'duplicate_phone';
const API_FIELDS: readonly (keyof CustomerInput)[] = ['name', 'phone', 'email', 'notes'];

function toCustomer(dto: CustomerDto): Customer {
  return {
    id: dto.id,
    name: dto.name,
    phone: dto.phone,
    email: dto.email,
    notes: dto.notes,
    active: dto.active,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function toBody(input: Partial<CustomerInput>): Record<string, string> {
  const body: Record<string, string> = {};
  for (const field of API_FIELDS) {
    const value = input[field];
    if (value !== undefined) body[field] = value;
  }
  return body;
}

function toFieldErrors(body: unknown): FieldErrors {
  const errors: FieldErrors = {};
  if (body && typeof body === 'object') {
    const record = body as Record<string, unknown>;
    for (const field of API_FIELDS) {
      const value = record[field];
      if (Array.isArray(value)) {
        errors[field] = value.map(String);
      }
    }
  }
  return errors;
}

function toMatches(body: unknown): DuplicateMatch[] {
  const matches = (body as { matches?: unknown } | null)?.matches;
  return Array.isArray(matches) ? (matches as DuplicateMatch[]) : [];
}

function isDuplicatePhone(body: unknown): boolean {
  return !!body && typeof body === 'object' && (body as { code?: unknown }).code === DUPLICATE_PHONE_CODE;
}

function toApiError(err: HttpErrorResponse): CustomerApiError {
  if (err.status === 0) {
    return new CustomerApiError(NETWORK_ERROR_MESSAGE, 0);
  }
  if (err.status === 400) {
    return new CustomerApiError(VALIDATION_ERROR_MESSAGE, 400, toFieldErrors(err.error));
  }
  if (err.status === 404) {
    return new CustomerApiError(NOT_FOUND_MESSAGE, 404);
  }
  if (err.status === 409 && isDuplicatePhone(err.error)) {
    return new DuplicateCustomerError(DUPLICATE_PHONE_MESSAGE, toMatches(err.error));
  }
  return new CustomerApiError(GENERIC_ERROR_MESSAGE, err.status);
}

@Injectable({
  providedIn: 'root',
})
export class CustomersApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/customers/`;

  list(params: CustomerListParams = {}): Observable<Page<Customer>> {
    let httpParams = new HttpParams();
    if (params.search) httpParams = httpParams.set('search', params.search);
    if (params.active !== undefined) httpParams = httpParams.set('active', String(params.active));
    if (params.page !== undefined) httpParams = httpParams.set('page', String(params.page));
    if (params.pageSize !== undefined) httpParams = httpParams.set('page_size', String(params.pageSize));
    return this.http.get<Page<CustomerDto>>(this.baseUrl, { params: httpParams }).pipe(
      map((page): Page<Customer> => ({ ...page, results: page.results.map(toCustomer) })),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err))),
    );
  }

  get(id: string): Observable<Customer> {
    return this.request(this.http.get<CustomerDto>(`${this.baseUrl}${id}/`));
  }

  /** Falla con `DuplicateCustomerError` si el teléfono ya existe y no se confirma el duplicado. */
  create(input: CustomerInput, confirmDuplicate = false): Observable<Customer> {
    const body: Record<string, string | boolean> = toBody(input);
    if (confirmDuplicate) body['confirm_duplicate'] = true;
    return this.request(this.http.post<CustomerDto>(this.baseUrl, body));
  }

  update(id: string, input: Partial<CustomerInput>): Observable<Customer> {
    return this.request(this.http.patch<CustomerDto>(`${this.baseUrl}${id}/`, toBody(input)));
  }

  activate(id: string): Observable<Customer> {
    return this.request(this.http.post<CustomerDto>(`${this.baseUrl}${id}/activate/`, {}));
  }

  deactivate(id: string): Observable<Customer> {
    return this.request(this.http.post<CustomerDto>(`${this.baseUrl}${id}/deactivate/`, {}));
  }

  private request(source: Observable<CustomerDto>): Observable<Customer> {
    return source.pipe(
      map(toCustomer),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err))),
    );
  }
}
