import { provideTestTranslations } from '../../../core/i18n/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../../environments/environment';
import { CrmCustomerPage } from '../models/crm-customer';
import { CrmApiError, CrmCustomersApiService } from './crm-customers-api.service';

describe('CrmCustomersApiService', () => {
  let service: CrmCustomersApiService;
  let http: HttpTestingController;
  const url = `${environment.apiUrl}/crm/customers/`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(CrmCustomersApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('sends only the filters that have a value and maps the rows', () => {
    let result: CrmCustomerPage | undefined;
    service.list({ search: 'ana', warehouseId: 'w-1', page: 2, pageSize: 10 }).subscribe((page) => (result = page));
    const req = http.expectOne((r) => r.url === url);
    expect(req.request.params.get('search')).toBe('ana');
    expect(req.request.params.get('warehouse_id')).toBe('w-1');
    expect(req.request.params.get('page')).toBe('2');
    expect(req.request.params.get('page_size')).toBe('10');
    req.flush({
      count: 1, next: null, previous: null,
      results: [{ customer_id: 'c-1', display_name: 'Ana', phone: '', last_purchase_at: '2026-11-10', order_count: 2, outstanding_amount: '30.00', currency: 'BOB' }],
      meta: { sales_enabled: true, warehouse_filter_enabled: false },
    });
    expect(result?.results[0]).toEqual({ id: 'c-1', name: 'Ana', phone: '', lastPurchaseAt: '2026-11-10', orderCount: 2, outstandingAmount: '30.00', currency: 'BOB' });
    expect(result?.meta.warehouse_filter_enabled).toBeFalse();
  });

  it('omits empty filters', () => {
    service.list({ search: '', warehouseId: '' }).subscribe();
    const req = http.expectOne((r) => r.url === url);
    expect(req.request.params.keys()).toEqual([]);
    req.flush({ count: 0, next: null, previous: null, results: [], meta: { sales_enabled: true, warehouse_filter_enabled: false } });
  });

  it('turns HTTP failures into a CrmApiError', () => {
    let error: unknown;
    service.list().subscribe({ error: (e) => (error = e) });
    http.expectOne((r) => r.url === url).flush({}, { status: 500, statusText: 'Server Error' });
    expect(error).toBeInstanceOf(CrmApiError);
    expect((error as CrmApiError).status).toBe(500);
  });
});

