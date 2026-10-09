import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { GENERIC_ERROR_MESSAGE, INVALID_PERIOD_MESSAGE, NETWORK_ERROR_MESSAGE, ReportingApiService } from './reporting-api.service';

const PERIOD = { kind: 'month', date_from: '2026-10-01', date_to: '2026-10-31' };

describe('ReportingApiService', () => {
  let service: ReportingApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(ReportingApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('asks for a named period with `period` and maps the dashboard (AC-25)', () => {
    let profit = '';
    let from = '';
    service.dashboard({ kind: 'week' }).subscribe((s) => {
      profit = s.estimatedProfit;
      from = s.period.dateFrom;
    });
    const req = http.expectOne((r) => r.url === '/api/reports/dashboard/');
    expect(req.request.params.get('period')).toBe('week');
    expect(req.request.params.has('date_from')).toBeFalse();
    req.flush({
      period: { ...PERIOD, kind: 'week', date_from: '2026-10-12' },
      sales_total: '1200.00',
      orders_count: 4,
      average_ticket: null,
      expenses_total: '450.00',
      estimated_profit: '750.00',
      pending_delivery_count: 3,
      pending_collection_count: 2,
      pending_collection_balance: '85.50',
      sales_criteria: 'criterio',
    });
    expect([profit, from]).toEqual(['750.00', '2026-10-12']);
  });

  it('asks for a range with date_from and date_to and no `period`', () => {
    service.sales({ kind: 'range', dateFrom: '2026-01-01', dateTo: '2026-03-31' }).subscribe();
    const req = http.expectOne((r) => r.url === '/api/reports/sales/');
    expect(req.request.params.get('date_from')).toBe('2026-01-01');
    expect(req.request.params.get('date_to')).toBe('2026-03-31');
    expect(req.request.params.has('period')).toBeFalse();
    req.flush({ period: PERIOD, total: '0.00', orders_count: 0, average_ticket: null, criteria: 'c' });
  });

  it('maps the expense breakdown, channels, products and customers', () => {
    const results: Record<string, unknown> = {};
    service.expenses({ kind: 'month' }).subscribe((r) => (results['expenses'] = r.categories[0]));
    http.expectOne((r) => r.url === '/api/reports/expenses/').flush({
      period: PERIOD,
      total: '20.00',
      categories: [{ category_id: 'c1', name: 'Empaque', active: false, total: '20.00' }],
    });
    service.salesByChannel({ kind: 'month' }).subscribe((r) => (results['channels'] = r.channels[0]));
    http.expectOne((r) => r.url === '/api/reports/sales-by-channel/').flush({
      period: PERIOD,
      channels: [{ sales_channel: 'STORE', orders_count: 1, total: '10.00' }],
    });
    service.topProducts({ kind: 'month' }).subscribe((r) => (results['products'] = r.products[0]));
    http.expectOne((r) => r.url === '/api/reports/top-products/').flush({
      period: PERIOD,
      limit: 10,
      products: [{ product_id: 'p1', product_name: 'Pack', units: 2, amount: '70.00' }],
    });
    service.topCustomers({ kind: 'month' }).subscribe((r) => (results['customers'] = r.customers[0]));
    http.expectOne((r) => r.url === '/api/reports/top-customers/').flush({
      period: PERIOD,
      limit: 10,
      customers: [{ customer_id: 'k1', name: 'Ana', orders_count: 2, total: '100.00' }],
    });
    expect(results['expenses']).toEqual({ categoryId: 'c1', name: 'Empaque', active: false, total: '20.00' });
    expect(results['channels']).toEqual({ salesChannel: 'STORE', ordersCount: 1, total: '10.00' });
    expect(results['products']).toEqual({ productId: 'p1', productName: 'Pack', units: 2, amount: '70.00' });
    expect(results['customers']).toEqual({ customerId: 'k1', name: 'Ana', ordersCount: 2, total: '100.00' });
  });

  it('maps the pending lists and sends no period (AC-25)', () => {
    let result: unknown;
    service.pending().subscribe((r) => (result = r));
    const req = http.expectOne('/api/reports/pending/');
    expect(req.request.params.keys()).toEqual([]);
    req.flush({
      delivery: {
        count: 1,
        rows: [{ id: 'o1', order_date: '2026-10-01', customer: null, total: '70.00', status: 'READY', payment_status: 'PAID', expected_delivery_date: null }],
      },
      collection: {
        count: 1,
        balance_total: '50.00',
        rows: [{ id: 'o2', order_date: '2026-10-02', customer: { id: 'k1', name: 'Ana' }, total: '70.00', balance: '50.00', status: 'DELIVERED', payment_status: 'PARTIAL' }],
      },
    });
    expect(result).toEqual({
      delivery: {
        count: 1,
        rows: [{ id: 'o1', orderDate: '2026-10-01', customer: null, expectedDeliveryDate: null, status: 'READY', paymentStatus: 'PAID', total: '70.00' }],
      },
      collection: {
        count: 1,
        balanceTotal: '50.00',
        rows: [{ id: 'o2', orderDate: '2026-10-02', customer: { id: 'k1', name: 'Ana' }, total: '70.00', balance: '50.00', status: 'DELIVERED', paymentStatus: 'PARTIAL' }],
      },
    });
  });

  it('turns failures into short messages', () => {
    const messages: string[] = [];
    service.sales({ kind: 'month' }).subscribe({ error: (e: Error) => messages.push(e.message) });
    http.expectOne((r) => r.url === '/api/reports/sales/').error(new ProgressEvent('error'));
    service.sales({ kind: 'month' }).subscribe({ error: (e: Error) => messages.push(e.message) });
    http.expectOne((r) => r.url === '/api/reports/sales/').flush({ period: ['x'] }, { status: 400, statusText: 'Bad Request' });
    service.pending().subscribe({ error: (e: Error) => messages.push(e.message) });
    http.expectOne('/api/reports/pending/').flush('boom', { status: 500, statusText: 'Server Error' });
    expect(messages).toEqual([NETWORK_ERROR_MESSAGE, INVALID_PERIOD_MESSAGE, GENERIC_ERROR_MESSAGE]);
  });
});
