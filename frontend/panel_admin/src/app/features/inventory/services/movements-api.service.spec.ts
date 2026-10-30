import { StockMovementDetail } from '../models/movement';
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

  it('posts the reason to reverse a movement and maps the counter-movement (API-01)', () => {
    let counter: StockMovementDetail | undefined;
    service.reverse('m-1', 'Error de carga').subscribe((result) => (counter = result));
    const req = http.expectOne('/api/stock-movements/m-1/reverse/');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ reason: 'Error de carga' });
    req.flush({
      ...DTO,
      id: 'm-2',
      kind: 'in',
      quantity: '2.5000',
      reason: 'Error de carga',
      user: { id: 'u-1', name: 'ana' },
      reverses: { id: 'm-1' },
      reversed_by: null,
      created_at: '2026-10-20T15:31:00Z',
    });
    expect(counter?.id).toBe('m-2');
    expect(counter?.reversesId).toBe('m-1');
  });

  it('maps reversal info and the expanded counter-movement in the detail (API-02)', () => {
    let detail: StockMovementDetail | undefined;
    service.get('m-1').subscribe((result) => (detail = result));
    http.expectOne('/api/stock-movements/m-1/').flush({
      ...DTO,
      quantity: '2.5000',
      reason: 'Venta',
      user: { id: 'u-1', name: 'ana' },
      reverses: null,
      created_at: '2026-10-20T15:30:01Z',
      reversal: { allowed: false, code: 'requires_return', message: 'Requiere devolución.' },
      reversed_by: { id: 'm-2', reference: 'PV-1', occurred_at: '2026-10-21T10:00:00Z', reason: 'Error', user: { name: 'bea' } },
    });
    expect(detail?.reversal).toEqual({ allowed: false, code: 'requires_return', message: 'Requiere devolución.' });
    expect(detail?.reversedBy).toEqual({ id: 'm-2', reference: 'PV-1', occurredAt: '2026-10-21T10:00:00Z', reason: 'Error', userName: 'bea' });
    expect(detail?.reversedById).toBe('m-2');
  });

  it('maps the 409 insufficient_stock and the 400 reason errors of a reversal (AC-01, AC-05)', () => {
    const errors: InventoryApiError[] = [];
    service.reverse('m-1', '').subscribe({ error: (err: InventoryApiError) => errors.push(err) });
    http.expectOne('/api/stock-movements/m-1/reverse/').flush({ reason: ['El motivo es obligatorio.'] }, { status: 400, statusText: 'x' });
    service.reverse('m-1', 'x').subscribe({ error: (err: InventoryApiError) => errors.push(err) });
    http.expectOne('/api/stock-movements/m-1/reverse/').flush(
      { detail: 'No hay saldo.', code: 'insufficient_stock', product: { name: 'Arroz' }, warehouse: { name: 'Central' }, unit: { abbreviation: 'kg' }, requested: '10.000', available: '2.000' },
      { status: 409, statusText: 'x' },
    );
    expect(errors[0].fieldErrors['reason']).toEqual(['El motivo es obligatorio.']);
    expect(errors[1].code).toBe('insufficient_stock');
    expect(errors[1].insufficientStock?.available).toBe('2.000');
  });
});
