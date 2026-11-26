import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { tr } from '../../../core/i18n/translate';
import { Page } from '../../../shared/models/page';
import { Recipe, RecipeApiError, RecipeDto, RecipeFieldErrors, RecipeInput, RecipeLineErrors, RecipeStatus } from '../models/recipe';

function fromDto(dto: RecipeDto): Recipe {
  return {
    id: dto.id,
    name: dto.name,
    resultProduct: dto.result_product,
    yieldQuantity: dto.yield_quantity,
    ingredients: dto.ingredients.map(line => ({
      productId: line.product_id, productName: line.product_name, productActive: line.product_active,
      unitId: line.unit_id, unitAbbreviation: line.unit_abbreviation, quantity: line.quantity,
    })),
    active: dto.active,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function toBody(input: RecipeInput): Record<string, unknown> {
  return {
    name: input.name.trim(),
    result_product_id: input.resultProductId,
    yield_quantity: input.yieldQuantity.trim(),
    ingredients: input.ingredients.map(line => ({
      product_id: line.productId, unit_id: line.unitId, quantity: line.quantity.trim(),
    })),
  };
}

function text(value: unknown): string | undefined {
  return Array.isArray(value) ? value.map(String).join(' ') : undefined;
}

function fieldErrors(body: unknown): RecipeFieldErrors {
  const errors: RecipeFieldErrors = { lines: {} };
  if (!body || typeof body !== 'object') return errors;
  const record = body as Record<string, unknown>;
  errors.name = text(record['name']);
  errors.resultProductId = text(record['result_product_id']);
  errors.yieldQuantity = text(record['yield_quantity']);
  const ingredients = record['ingredients'];
  if (Array.isArray(ingredients)) {
    ingredients.forEach((item, index) => {
      if (typeof item === 'string') errors.ingredients = [errors.ingredients, item].filter(Boolean).join(' ');
      else if (item && typeof item === 'object' && Object.keys(item).length) {
        const line = item as Record<string, unknown>;
        const mapped: RecipeLineErrors = {
          productId: text(line['product_id']), unitId: text(line['unit_id']), quantity: text(line['quantity']),
        };
        errors.lines[index] = mapped;
      }
    });
  }
  return errors;
}

function apiError(error: HttpErrorResponse): Observable<never> {
  const body: unknown = error.error;
  const invalidPage = error.status === 400 && !!body && typeof body === 'object' && Array.isArray((body as Record<string, unknown>)['page']);
  const message = error.status === 0 ? tr('PRODUCTION.RECIPES.ERRORS.NETWORK')
    : error.status === 400 ? tr('PRODUCTION.RECIPES.ERRORS.VALIDATION')
    : error.status === 403 ? tr('PRODUCTION.RECIPES.ERRORS.FORBIDDEN')
    : error.status === 404 ? tr('PRODUCTION.RECIPES.ERRORS.NOT_FOUND') : tr('PRODUCTION.RECIPES.ERRORS.GENERIC');
  return throwError(() => new RecipeApiError(message, error.status, fieldErrors(body), invalidPage));
}

@Injectable({ providedIn: 'root' })
export class RecipesApiService {
  private http = inject(HttpClient);
  private url = `${environment.apiUrl}/recipes/`;

  list(params: { search?: string; status?: RecipeStatus; page?: number; pageSize?: number } = {}): Observable<Page<Recipe>> {
    let query = new HttpParams();
    if (params.search) query = query.set('q', params.search);
    if (params.status) query = query.set('status', params.status);
    if (params.page) query = query.set('page', params.page);
    if (params.pageSize) query = query.set('page_size', params.pageSize);
    return this.http.get<Page<RecipeDto>>(this.url, { params: query }).pipe(
      map(page => ({ ...page, results: page.results.map(fromDto) })), catchError(apiError));
  }

  get(id: string): Observable<Recipe> {
    return this.request(this.http.get<RecipeDto>(`${this.url}${id}/`));
  }

  create(input: RecipeInput): Observable<Recipe> {
    return this.request(this.http.post<RecipeDto>(this.url, toBody(input)));
  }

  update(id: string, input: RecipeInput): Observable<Recipe> {
    return this.request(this.http.put<RecipeDto>(`${this.url}${id}/`, toBody(input)));
  }

  setActive(id: string, active: boolean): Observable<Recipe> {
    return this.request(this.http.post<RecipeDto>(`${this.url}${id}/${active ? 'activate' : 'deactivate'}/`, {}));
  }

  private request(source: Observable<RecipeDto>): Observable<Recipe> {
    return source.pipe(map(fromDto), catchError(apiError));
  }
}

@Injectable({ providedIn: 'root' })
export class RecipeFiltersState {
  search = '';
  status: RecipeStatus = 'active';
  pageIndex = 0;
}
