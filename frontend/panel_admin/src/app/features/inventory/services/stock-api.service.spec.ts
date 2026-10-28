import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { InventoryApiError } from '../models/api-error';
import { OpeningInput, formatQuantity, newUuid, quantityError, todayIso } from '../models/stock';
import { StockApiService } from './stock-api.service';

const INPUT: OpeningInput = {
  openingId: 'o-1',
  warehouseId: 'w-1',
  movementDate: '2026-10-27',
  reference: 'Inventario inicial',
  lines: [{ productId: 'p-1', quantity: '10' }],
};

describe('StockApiService', () => {
  let http: HttpTestingController;
  let service: StockApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    http = TestBed.inject(HttpTestingController);
    service = TestBed.inject(StockApiService);
  });

  afterEach(() => http.verify());

  it('lists balances filtered by warehouse and maps them (AC-05)', () => {
    let first: unknown;
    service.list({ warehouseId: 'w-1', page: 2, pageSize: 20 }).subscribe((page) => (first = page.results[0]));
    const req = http.expectOne((r) => r.url.endsWith('/stock/'));
    expect(req.request.params.get('warehouse_id')).toBe('w-1');
    expect(req.request.params.get('page')).toBe('2');
    req.flush({
      count: 1,
      next: null,
      previous: null,
      results: [
        {
          product_id: 'p-1',
          product_name: 'Harina',
          warehouse_id: 'w-1',
          warehouse_name: 'Principal',
          quantity: '10.000',
          unit: { abbreviation: 'u', allows_fractions: false },
        },
      ],
    });
    expect(first).toEqual({
      productId: 'p-1',
      productName: 'Harina',
      warehouseId: 'w-1',
      warehouseName: 'Principal',
      quantity: '10.000',
      unit: { abbreviation: 'u', allowsFractions: false },
    });
  });

  it('asks which products already have history, repeating product_id (AC-03)', () => {
    let ids: string[] = [];
    service.productsWithHistory('w-1', ['p-1', 'p-2']).subscribe((value) => (ids = value));
    const req = http.expectOne((r) => r.url.endsWith('/stock/opening-check/'));
    expect(req.request.params.getAll('product_id')).toEqual(['p-1', 'p-2']);
    req.flush({ products_with_history: ['p-2'] });
    expect(ids).toEqual(['p-2']);
  });

  it('posts the opening in snake_case with its idempotency key (AC-01, AC-02)', () => {
    let result: unknown;
    service.register(INPUT).subscribe((value) => (result = value));
    const req = http.expectOne((r) => r.url.endsWith('/stock/openings/'));
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      opening_id: 'o-1',
      warehouse_id: 'w-1',
      movement_date: '2026-10-27',
      reference: 'Inventario inicial',
      lines: [{ product_id: 'p-1', quantity: '10' }],
    });
    req.flush({
      opening_id: 'o-1',
      warehouse_id: 'w-1',
      movement_date: '2026-10-27',
      reference: 'Inventario inicial',
      lines: [
        { product_id: 'p-1', quantity: '10.000', movement_id: 'm-1' },
        { product_id: 'p-2', quantity: '0.000', movement_id: null },
      ],
    });
    expect(result).toEqual({
      openingId: 'o-1',
      warehouseId: 'w-1',
      movementDate: '2026-10-27',
      reference: 'Inventario inicial',
      lines: [
        { productId: 'p-1', quantity: '10.000', movementId: 'm-1' },
        { productId: 'p-2', quantity: '0.000', movementId: null },
      ],
    });
  });

  it('maps line errors (400) and history conflicts (409) (AC-03, EDGE-02)', () => {
    const errors: InventoryApiError[] = [];
    service.register(INPUT).subscribe({ error: (e) => errors.push(e) });
    http.expectOne((r) => r.url.endsWith('/stock/openings/')).flush(
      { reference: ['Obligatoria'], lines: [{ quantity: ['Sin fracciones'] }] },
      { status: 400, statusText: 'Bad Request' },
    );
    service.register(INPUT).subscribe({ error: (e) => errors.push(e) });
    http.expectOne((r) => r.url.endsWith('/stock/openings/')).flush(
      { detail: 'Ya tienen movimientos.', code: 'stock_history_exists', lines: [{ index: '0', product_id: 'p-1' }] },
      { status: 409, statusText: 'Conflict' },
    );
    expect(errors[0].fieldErrors['reference']).toEqual(['Obligatoria']);
    expect(errors[0].lineErrors).toEqual([{ quantity: ['Sin fracciones'] }]);
    expect(errors[1].code).toBe('stock_history_exists');
    expect(errors[1].historyProductIds).toEqual(['p-1']);
  });
});

describe('stock model helpers', () => {
  it('validates quantities: non-negative, up to 3 decimals, integer without fractions (EDGE-02)', () => {
    expect(quantityError('0', false)).toBeNull();
    expect(quantityError('2.500', true)).toBeNull();
    expect(quantityError('3.000', false)).toBeNull();
    expect(quantityError('', true)).not.toBeNull();
    expect(quantityError('-1', true)).not.toBeNull();
    expect(quantityError('1e3', true)).not.toBeNull();
    expect(quantityError('1.0005', true)).not.toBeNull();
    expect(quantityError('1.5', false)).toContain('no admite fracciones');
  });

  it('formats quantities without trailing zeros', () => {
    expect(formatQuantity('10.000')).toBe('10');
    expect(formatQuantity('2.500')).toBe('2.5');
    expect(formatQuantity('0.000')).toBe('0');
    expect(formatQuantity('100')).toBe('100');
  });

  it('builds local ISO dates and unique keys', () => {
    expect(todayIso(new Date(2026, 9, 5))).toBe('2026-10-05');
    expect(newUuid()).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12}$/);
    expect(newUuid()).not.toBe(newUuid());
  });
});
