import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  FieldErrors,
  Product,
  ProductApiError,
  ProductDto,
  ProductInput,
  ProductListParams,
} from '../models/product';
import { Page } from '../../../shared/models/page';

export const NETWORK_ERROR_MESSAGE = 'No se pudo conectar con el servidor. Inténtalo de nuevo.';
export const NOT_FOUND_MESSAGE = 'Producto no encontrado.';
export const GENERIC_ERROR_MESSAGE = 'Ocurrió un error inesperado. Inténtalo de nuevo.';
export const VALIDATION_ERROR_MESSAGE = 'Revisa los datos ingresados.';

const API_FIELDS: Record<string, keyof ProductInput> = {
  name: 'name',
  description: 'description',
  sale_price: 'salePrice',
  tracks_stock: 'tracksStock',
  base_unit_id: 'baseUnitId',
};

function toProduct(dto: ProductDto): Product {
  return {
    id: dto.id,
    name: dto.name,
    description: dto.description,
    salePrice: dto.sale_price,
    active: dto.active,
    tracksStock: dto.tracks_stock,
    baseUnit: dto.base_unit,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function toBody(input: Partial<ProductInput>): Record<string, string | boolean | null> {
  const body: Record<string, string | boolean | null> = {};
  if (input.name !== undefined) body['name'] = input.name;
  if (input.description !== undefined) body['description'] = input.description;
  if (input.salePrice !== undefined) body['sale_price'] = input.salePrice;
  if (input.tracksStock !== undefined) body['tracks_stock'] = input.tracksStock;
  if (input.baseUnitId !== undefined) body['base_unit_id'] = input.baseUnitId;
  return body;
}

function toFieldErrors(body: unknown): FieldErrors {
  const errors: FieldErrors = {};
  if (body && typeof body === 'object') {
    for (const [apiField, value] of Object.entries(body)) {
      const field = API_FIELDS[apiField];
      if (field && Array.isArray(value)) {
        errors[field] = value.map(String);
      }
    }
  }
  return errors;
}

function toApiError(err: HttpErrorResponse): ProductApiError {
  if (err.status === 0) {
    return new ProductApiError(NETWORK_ERROR_MESSAGE, 0);
  }
  if (err.status === 400) {
    return new ProductApiError(VALIDATION_ERROR_MESSAGE, 400, toFieldErrors(err.error));
  }
  if (err.status === 404) {
    return new ProductApiError(NOT_FOUND_MESSAGE, 404);
  }
  if (err.status === 409) {
    const body = (err.error && typeof err.error === 'object' ? err.error : {}) as { detail?: unknown; code?: unknown };
    const detail = typeof body.detail === 'string' ? body.detail : GENERIC_ERROR_MESSAGE;
    return new ProductApiError(detail, 409, {}, typeof body.code === 'string' ? body.code : null);
  }
  return new ProductApiError(GENERIC_ERROR_MESSAGE, err.status);
}

@Injectable({
  providedIn: 'root',
})
export class ProductsApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/products/`;

  list(params: ProductListParams = {}): Observable<Page<Product>> {
    let httpParams = new HttpParams();
    if (params.search) httpParams = httpParams.set('search', params.search);
    if (params.active !== undefined) httpParams = httpParams.set('active', String(params.active));
    if (params.page !== undefined) httpParams = httpParams.set('page', String(params.page));
    if (params.pageSize !== undefined) httpParams = httpParams.set('page_size', String(params.pageSize));
    return this.http.get<Page<ProductDto>>(this.baseUrl, { params: httpParams }).pipe(
      map((page): Page<Product> => ({ ...page, results: page.results.map(toProduct) })),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err))),
    );
  }

  get(id: string): Observable<Product> {
    return this.request(this.http.get<ProductDto>(`${this.baseUrl}${id}/`));
  }

  create(input: ProductInput): Observable<Product> {
    return this.request(this.http.post<ProductDto>(this.baseUrl, toBody(input)));
  }

  update(id: string, input: Partial<ProductInput>): Observable<Product> {
    return this.request(this.http.patch<ProductDto>(`${this.baseUrl}${id}/`, toBody(input)));
  }

  activate(id: string): Observable<Product> {
    return this.request(this.http.post<ProductDto>(`${this.baseUrl}${id}/activate/`, {}));
  }

  deactivate(id: string): Observable<Product> {
    return this.request(this.http.post<ProductDto>(`${this.baseUrl}${id}/deactivate/`, {}));
  }

  private request(source: Observable<ProductDto>): Observable<Product> {
    return source.pipe(
      map(toProduct),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err))),
    );
  }
}
