import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { MovementValuationDto } from '../models/movement-valuation';
import { MovementValuationApiService } from './movement-valuation-api.service';

const DTO: MovementValuationDto = {
  id: 7,
  movement_id: 'm-1',
  product_id: 'p-1',
  product_name: 'Harina',
  unit_abbreviation: 'kg',
  kind: 'in',
  quantity: '4.0000',
  unit_cost: '8.000000',
  value: '32.00',
  average_before: '5.000000',
  average_after: '5.857143',
  cost_origin: 'purchase_price',
  source_type: 'purchase_receipt',
  source_id: 'r-1',
  source_label: 'Recepción de compra',
  reverses_movement_id: null,
  occurred_at: '2026-10-30T15:00:00Z',
  status: 'valued',
};

describe('MovementValuationApiService', () => {
  let http: HttpTestingController;
  let service: MovementValuationApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    http = TestBed.inject(HttpTestingController);
    service = TestBed.inject(MovementValuationApiService);
  });

  afterEach(() => http.verify());

  it('sends the filters in snake_case and maps the snapshot (AC-18)', () => {
    let first = '';
    let average = '';
    service
      .list({ dateFrom: '2026-10-01', dateTo: '2026-10-31', productId: 'p-1', sourceType: 'purchase_receipt', sourceId: 'r-1', page: 2, pageSize: 10 })
      .subscribe((page) => {
        first = page.results[0].productName;
        average = page.results[0].averageAfter;
      });
    const req = http.expectOne((r) => r.url.endsWith('/valuation/movements/'));
    expect(req.request.params.get('date_from')).toBe('2026-10-01');
    expect(req.request.params.get('date_to')).toBe('2026-10-31');
    expect(req.request.params.get('product_id')).toBe('p-1');
    expect(req.request.params.get('source_type')).toBe('purchase_receipt');
    expect(req.request.params.get('source_id')).toBe('r-1');
    expect(req.request.params.get('page')).toBe('2');
    expect(req.request.params.get('page_size')).toBe('10');
    req.flush({ count: 1, next: null, previous: null, results: [DTO] });
    expect([first, average]).toEqual(['Harina', '5.857143']);
  });

  it('does not send source_id without source_type and can filter by movement', () => {
    service.list({ sourceId: 'r-1', movementId: 'm-1' }).subscribe();
    const req = http.expectOne((r) => r.url.endsWith('/valuation/movements/'));
    expect(req.request.params.has('source_id')).toBeFalse();
    expect(req.request.params.get('movement_id')).toBe('m-1');
    req.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('turns HTTP failures into friendly errors', () => {
    const messages: string[] = [];
    service.list().subscribe({ error: (err: Error) => messages.push(err.message) });
    http.expectOne((r) => r.url.endsWith('/valuation/movements/')).flush({ detail: 'No tiene permiso.' }, { status: 403, statusText: 'Forbidden' });
    service.list().subscribe({ error: (err: Error) => messages.push(err.message) });
    http.expectOne((r) => r.url.endsWith('/valuation/movements/')).error(new ProgressEvent('error'));
    expect(messages).toEqual(['No tiene permiso.', 'No se pudo conectar con el servidor. Inténtalo de nuevo.']);
  });
});
