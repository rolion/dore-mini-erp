import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { StockAdjustmentDetail } from '../models/adjustment';
import { InventoryApiError } from '../models/api-error';
import { AdjustmentsApiService } from './adjustments-api.service';

const DTO = {
  id: 'a-1',
  reference: 'AJ-1A2B3C4D',
  created_at: '2026-10-20T15:30:00Z',
  product: { id: 'p-1', name: 'Arroz' },
  warehouse: { id: 'w-1', name: 'Central' },
  system_quantity: '10.0000',
  counted_quantity: '7.0000',
  difference: '-3.0000',
  kind: 'out',
  unit: { abbreviation: 'kg' },
  user: { id: 'u-1', name: 'ana' },
  status: 'confirmed',
  reason: 'Conteo físico',
  movement: { id: 'm-9' },
};

const INPUT = {
  adjustmentId: 'a-1',
  productId: 'p-1',
  warehouseId: 'w-1',
  countedQuantity: '7',
  expectedSystemQuantity: '10.0000',
  reason: 'Conteo físico',
};

describe('AdjustmentsApiService', () => {
  let http: HttpTestingController;
  let service: AdjustmentsApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    http = TestBed.inject(HttpTestingController);
    service = TestBed.inject(AdjustmentsApiService);
  });

  afterEach(() => http.verify());

  it('sends the filters in snake_case and maps the rows (AC-05)', () => {
    let first: string | undefined;
    service
      .list({ dateFrom: '2026-10-01', dateTo: '2026-10-31', productId: 'p-1', warehouseId: 'w-1', page: 2, pageSize: 25 })
      .subscribe((page) => (first = page.results[0].difference));
    const req = http.expectOne((r) => r.url.endsWith('/stock-adjustments/'));
    expect(req.request.params.get('date_from')).toBe('2026-10-01');
    expect(req.request.params.get('date_to')).toBe('2026-10-31');
    expect(req.request.params.get('product_id')).toBe('p-1');
    expect(req.request.params.get('warehouse_id')).toBe('w-1');
    expect(req.request.params.get('page')).toBe('2');
    req.flush({ count: 1, next: null, previous: null, results: [DTO] });
    expect(first).toBe('-3.0000');
  });

  it('reads the detail with the reason and the movement (AC-06)', () => {
    let detail: StockAdjustmentDetail | undefined;
    service.get('a-1').subscribe((value) => (detail = value));
    http.expectOne((r) => r.url.endsWith('/stock-adjustments/a-1/')).flush(DTO);
    expect(detail?.reason).toBe('Conteo físico');
    expect(detail?.movementId).toBe('m-9');
    expect(detail?.unitAbbreviation).toBe('kg');
  });

  it('asks for the current balance of a product in a warehouse', () => {
    let quantity = '';
    service.balance('p-1', 'w-1').subscribe((balance) => (quantity = balance.systemQuantity));
    const req = http.expectOne((r) => r.url.endsWith('/stock-adjustments/balance/'));
    expect(req.request.params.get('product_id')).toBe('p-1');
    expect(req.request.params.get('warehouse_id')).toBe('w-1');
    req.flush({ system_quantity: '10.0000', unit: { abbreviation: 'kg', allows_fractions: true } });
    expect(quantity).toBe('10.0000');
  });

  it('posts the idempotency key and the expected balance, never the difference (AC-01, AC-07)', () => {
    service.confirm(INPUT).subscribe();
    const req = http.expectOne((r) => r.url.endsWith('/stock-adjustments/'));
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      adjustment_id: 'a-1',
      product_id: 'p-1',
      warehouse_id: 'w-1',
      counted_quantity: '7',
      expected_system_quantity: '10.0000',
      reason: 'Conteo físico',
    });
    req.flush(DTO, { status: 201, statusText: 'Created' });
  });

  it('exposes the current balance of a 409 balance_changed (AC-03)', () => {
    let error: InventoryApiError | undefined;
    service.confirm(INPUT).subscribe({ error: (err: InventoryApiError) => (error = err) });
    http.expectOne((r) => r.url.endsWith('/stock-adjustments/')).flush(
      { detail: 'El saldo cambió', code: 'balance_changed', current_balance: '7.0000' },
      { status: 409, statusText: 'Conflict' },
    );
    expect(error?.code).toBe('balance_changed');
    expect(error?.currentBalance).toBe('7.0000');
  });

  it('maps field errors of a 400 to the form fields', () => {
    let error: InventoryApiError | undefined;
    service.confirm(INPUT).subscribe({ error: (err: InventoryApiError) => (error = err) });
    http.expectOne((r) => r.url.endsWith('/stock-adjustments/')).flush(
      { reason: ['El motivo es obligatorio.'], counted_quantity: ['No válida'] },
      { status: 400, statusText: 'Bad Request' },
    );
    expect(error?.fieldErrors['reason']).toEqual(['El motivo es obligatorio.']);
    expect(error?.fieldErrors['countedQuantity']).toEqual(['No válida']);
  });
});
