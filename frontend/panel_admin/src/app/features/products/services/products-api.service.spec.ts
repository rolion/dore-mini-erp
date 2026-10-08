import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { Product, ProductApiError, ProductDto } from '../models/product';
import {
  GENERIC_ERROR_MESSAGE,
  NETWORK_ERROR_MESSAGE,
  NOT_FOUND_MESSAGE,
  ProductsApiService,
} from './products-api.service';

const DTO: ProductDto = {
  id: 'abc',
  name: 'Cuñapé',
  description: 'Tradicional',
  sale_price: '35.00',
  active: true,
  created_at: '2026-10-08T10:00:00Z',
  updated_at: '2026-10-08T11:00:00Z',
};

const PRODUCT: Product = {
  id: 'abc',
  name: 'Cuñapé',
  description: 'Tradicional',
  salePrice: '35.00',
  active: true,
  createdAt: '2026-10-08T10:00:00Z',
  updatedAt: '2026-10-08T11:00:00Z',
};

describe('ProductsApiService', () => {
  let service: ProductsApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ProductsApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  /** Se suscribe ya (lo que dispara la petición) y entrega el error cuando llega la respuesta simulada. */
  function watchError(source: { subscribe: (o: { error: (e: unknown) => void }) => unknown }): { error: ProductApiError } {
    const holder = { error: undefined as unknown as ProductApiError };
    source.subscribe({ error: (e) => (holder.error = e as ProductApiError) });
    return holder;
  }

  it('lists products sending search, active, page and page_size (AC-06, AC-10)', () => {
    let result: unknown;
    service.list({ search: 'cu', active: false, page: 2, pageSize: 10 }).subscribe((p) => (result = p));

    const req = http.expectOne((r) => r.url === '/api/products/');
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('search')).toBe('cu');
    expect(req.request.params.get('active')).toBe('false');
    expect(req.request.params.get('page')).toBe('2');
    expect(req.request.params.get('page_size')).toBe('10');
    req.flush({ count: 1, next: null, previous: null, results: [DTO] });

    expect(result).toEqual({ count: 1, next: null, previous: null, results: [PRODUCT] });
  });

  it('omits empty filters when listing (AC-06)', () => {
    service.list({ search: '' }).subscribe();
    const req = http.expectOne((r) => r.url === '/api/products/');
    expect(req.request.params.keys()).toEqual([]);
    req.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('gets one product (AC-13)', () => {
    let result: unknown;
    service.get('abc').subscribe((p) => (result = p));
    const req = http.expectOne('/api/products/abc/');
    expect(req.request.method).toBe('GET');
    req.flush(DTO);
    expect(result).toEqual(PRODUCT);
  });

  it('creates a product posting snake_case body with the price as text (AC-01, AC-12)', () => {
    let result: unknown;
    service
      .create({ name: 'Cuñapé', description: 'Tradicional', salePrice: '35.00' })
      .subscribe((p) => (result = p));
    const req = http.expectOne('/api/products/');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ name: 'Cuñapé', description: 'Tradicional', sale_price: '35.00' });
    req.flush(DTO);
    expect(result).toEqual(PRODUCT);
  });

  it('updates a product with PATCH (AC-04)', () => {
    service.update('abc', { name: 'Nuevo' }).subscribe();
    const req = http.expectOne('/api/products/abc/');
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ name: 'Nuevo' });
    req.flush(DTO);
  });

  it('activates and deactivates with POST to the action endpoints (AC-05, AC-11)', () => {
    let activated: Product | undefined;
    service.activate('abc').subscribe((p) => (activated = p));
    const activate = http.expectOne('/api/products/abc/activate/');
    expect(activate.request.method).toBe('POST');
    activate.flush(DTO);
    expect(activated?.active).toBeTrue();

    let deactivated: Product | undefined;
    service.deactivate('abc').subscribe((p) => (deactivated = p));
    const deactivate = http.expectOne('/api/products/abc/deactivate/');
    expect(deactivate.request.method).toBe('POST');
    deactivate.flush({ ...DTO, active: false });
    expect(deactivated?.active).toBeFalse();
  });

  it('maps 400 responses to per-field errors using form field names (AC-12)', () => {
    const watched = watchError(service.create({ name: '', description: '', salePrice: '-1' }));
    const req = http.expectOne('/api/products/');
    req.flush(
      { name: ['El nombre es obligatorio.'], sale_price: ['No negativo.'], other: ['ignorado'] },
      { status: 400, statusText: 'Bad Request' },
    );
    const error = watched.error;
    expect(error instanceof ProductApiError).toBeTrue();
    expect(error.status).toBe(400);
    expect(error.fieldErrors).toEqual({ name: ['El nombre es obligatorio.'], salePrice: ['No negativo.'] });
  });

  it('maps 404, network and other failures to friendly errors (AC-13)', () => {
    const notFound = watchError(service.get('x'));
    http.expectOne('/api/products/x/').flush({ detail: 'x' }, { status: 404, statusText: 'Not Found' });
    expect(notFound.error.status).toBe(404);
    expect(notFound.error.message).toBe(NOT_FOUND_MESSAGE);

    const network = watchError(service.get('y'));
    http.expectOne('/api/products/y/').error(new ProgressEvent('error'));
    expect(network.error.status).toBe(0);
    expect(network.error.message).toBe(NETWORK_ERROR_MESSAGE);

    const server = watchError(service.list());
    http.expectOne((r) => r.url === '/api/products/').flush('boom', { status: 500, statusText: 'Server Error' });
    expect(server.error.status).toBe(500);
    expect(server.error.message).toBe(GENERIC_ERROR_MESSAGE);
  });
});
