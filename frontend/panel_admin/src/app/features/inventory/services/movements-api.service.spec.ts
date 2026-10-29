import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { InventoryApiError } from '../models/api-error';
import { StockMovement } from '../models/movement';
import { MovementsApiService } from './movements-api.service';

const DTO = {
  id: 'm-1',
  occurred_at: '2026-10-20T15:30:00Z',
  reference: 'PV-1',
  product: { id: 'p-1', name: 'Arroz' },
  warehouse: { id: 'w-1', name: 'Central' },
  kind: 'out',
  quantity_in: null,
  quantity_out: '2.5000',
  unit: { abbreviation: 'kg' },
  status: 'confirmed',
  source: { type: 'sales_order', label: 'Pedido de venta', id: '42', line: '', reference: 'PV-1', available: true },
};

describe('MovementsApiService', () => {
  let http: HttpTestingController;
  let service: MovementsApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    http = TestBed.inject(HttpTestingController);
    service = TestBed.inject(MovementsApiService);
  });

  afterEach(() => http.verify());

  it('sends filters in snake_case and maps entries and exits to separate fields (AC-04, AC-05)', () => {
    let row: StockMovement | undefined;
    service
      .list({
        dateFrom: '2026-10-01',
        dateTo: '2026-10-31',
        productId: 'p-1',
        warehouseId: 'w-1',
        kind: 'out',
        sourceType: 'none',
        page: 2,
        pageSize: 10,
      })
      .subscribe((page) => (row = page.results[0]));
    const req = http.expectOne((r) => r.url.endsWith('/stock-movements/'));
    expect(req.request.method).toBe('GET');
    expect(req.request.params.keys().sort()).toEqual([
      'date_from',
      'date_to',
      'kind',
      'page',
      'page_size',
      'product_id',
      'source_type',
      'warehouse_id',
    ]);
    expect(req.request.params.get('source_type')).toBe('none');
    req.flush({ count: 1, next: null, previous: null, results: [DTO] });
    expect(row?.quantityIn).toBeNull();
    expect(row?.quantityOut).toBe('2.5000');
    expect(row?.unitAbbreviation).toBe('kg');
  });

  it('omits empty filters', () => {
    service.list({ productId: '', kind: undefined }).subscribe();
    const req = http.expectOne((r) => r.url.endsWith('/stock-movements/'));
    expect(req.request.params.keys()).toEqual([]);
    req.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('maps the detail with counter-movement links (AC-06)', () => {
    let reversedBy = '' as string | null;
    service.get('m-1').subscribe((detail) => (reversedBy = detail.reversedById));
    const req = http.expectOne((r) => r.url.endsWith('/stock-movements/m-1/'));
    req.flush({
      ...DTO,
      quantity: '2.5000',
      reason: 'Venta',
      user: { id: 'u', name: 'ana' },
      reversed_by: { id: 'm-2' },
      reverses: null,
      created_at: '2026-10-20T15:30:01Z',
    });
    expect(reversedBy).toBe('m-2');
  });

  it('translates a 404 into an API error', () => {
    let error: InventoryApiError | undefined;
    service.get('x').subscribe({ error: (err: InventoryApiError) => (error = err) });
    http
      .expectOne((r) => r.url.endsWith('/stock-movements/x/'))
      .flush({ detail: 'Movimiento no encontrado.' }, { status: 404, statusText: 'Not Found' });
    expect(error?.status).toBe(404);
  });

  it('sends the source document id only together with its class (API-04)', () => {
    service.list({ sourceType: 'sales_order', sourceId: 'o-42' }).subscribe();
    const req = http.expectOne((r) => r.url === '/api/stock-movements/');
    expect(req.request.params.get('source_type')).toBe('sales_order');
    expect(req.request.params.get('source_id')).toBe('o-42');
    req.flush({ count: 0, next: null, previous: null, results: [] });
    service.list({ sourceId: 'o-42' }).subscribe();
    const bare = http.expectOne((r) => r.url === '/api/stock-movements/');
    expect(bare.request.params.has('source_id')).toBeFalse();
    bare.flush({ count: 0, next: null, previous: null, results: [] });
  });
});
