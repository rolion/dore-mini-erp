import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { InventoryApiError } from '../models/api-error';
import { StockLot, StockLotDto } from '../models/lot';
import { LotsApiService } from './lots-api.service';

export const LOT_DTO: StockLotDto = {
  id: 'l-1',
  code: 'L-20261126-0001',
  status: 'refrigerating',
  lot_date: '2026-11-26',
  fiscal_period_name: 'Gestión 2026',
  product_id: 'p-1',
  product_name: 'Cuñapé granel',
  product_active: true,
  unit: { abbreviation: 'u', allows_fractions: false },
  warehouse_id: 'w-1',
  warehouse_name: 'Principal',
  physical_quantity: '118.0000',
  available_quantity: '0.0000',
  created_at: '2026-11-26T15:00:00Z',
  released_at: null,
  released_by_name: '',
};

describe('LotsApiService', () => {
  let http: HttpTestingController;
  let service: LotsApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    http = TestBed.inject(HttpTestingController);
    service = TestBed.inject(LotsApiService);
  });

  afterEach(() => http.verify());

  it('lists lots with their physical and available quantities (AC-11, AC-14)', () => {
    let first: StockLot | undefined;
    service.list({ page: 2, pageSize: 10 }).subscribe((page) => (first = page.results[0]));
    const req = http.expectOne((r) => r.url.endsWith('/stock-lots/'));
    expect(req.request.params.get('page')).toBe('2');
    expect(req.request.params.get('page_size')).toBe('10');
    req.flush({ count: 1, next: null, previous: null, results: [LOT_DTO] });
    expect(first).toEqual({
      id: 'l-1',
      code: 'L-20261126-0001',
      status: 'refrigerating',
      lotDate: '2026-11-26',
      fiscalPeriodName: 'Gestión 2026',
      productId: 'p-1',
      productName: 'Cuñapé granel',
      productActive: true,
      unit: { abbreviation: 'u', allowsFractions: false },
      warehouseId: 'w-1',
      warehouseName: 'Principal',
      physicalQuantity: '118.0000',
      availableQuantity: '0.0000',
      createdAt: '2026-11-26T15:00:00Z',
      releasedAt: null,
      releasedByName: '',
    });
  });

  it('sends only the filters that were chosen', () => {
    service.list({ search: 'L-2026', productId: 'p-1', warehouseId: 'w-1', status: 'released', withStock: true }).subscribe();
    const req = http.expectOne((r) => r.url.endsWith('/stock-lots/'));
    expect(req.request.params.get('search')).toBe('L-2026');
    expect(req.request.params.get('product_id')).toBe('p-1');
    expect(req.request.params.get('warehouse_id')).toBe('w-1');
    expect(req.request.params.get('status')).toBe('released');
    expect(req.request.params.get('with_stock')).toBe('true');
    req.flush({ count: 0, next: null, previous: null, results: [] });

    service.list({ withStock: false }).subscribe();
    const bare = http.expectOne((r) => r.url.endsWith('/stock-lots/'));
    expect(bare.request.params.keys()).toEqual([]);
    bare.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('turns server errors into InventoryApiError', () => {
    let error: InventoryApiError | undefined;
    service.list().subscribe({ error: (err: InventoryApiError) => (error = err) });
    http.expectOne((r) => r.url.endsWith('/stock-lots/')).flush({ detail: 'Sin permiso.' }, { status: 403, statusText: 'Forbidden' });
    expect(error?.status).toBe(403);
  });
});
