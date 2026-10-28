import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, of } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import { OpeningProduct } from '../models/stock';

interface ProductOptionDto {
  id: string;
  name: string;
  base_unit: { name: string; abbreviation: string; allows_fractions?: boolean } | null;
}

export const PRODUCT_OPTIONS_PAGE_SIZE = 50;

/** Productos que se ofrecen en la apertura: activos y con control de stock (el servidor vuelve a validar). */
@Injectable({
  providedIn: 'root',
})
export class OpeningProductsService {
  private http = inject(HttpClient);
  private readonly url = `${environment.apiUrl}/products/`;

  search(term: string | null): Observable<OpeningProduct[]> {
    let params = new HttpParams()
      .set('active', 'true')
      .set('tracks_stock', 'true')
      .set('page_size', String(PRODUCT_OPTIONS_PAGE_SIZE));
    if (term?.trim()) {
      params = params.set('search', term.trim());
    }
    return this.http.get<Page<ProductOptionDto>>(this.url, { params }).pipe(
      map((page) =>
        page.results
          .filter((dto) => dto.base_unit !== null)
          .map(
            (dto): OpeningProduct => ({
              id: dto.id,
              name: dto.name,
              unit: {
                name: dto.base_unit?.name ?? '',
                abbreviation: dto.base_unit?.abbreviation ?? '',
                allowsFractions: dto.base_unit?.allows_fractions ?? false,
              },
            }),
          ),
      ),
      catchError(() => of([] as OpeningProduct[])),
    );
  }
}
