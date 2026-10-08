import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { CustomerOrdersApiService, HISTORY_ERROR_MESSAGE } from './customer-orders-api.service';

describe('CustomerOrdersApiService', () => {
  let service: CustomerOrdersApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(CustomerOrdersApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('asks Sales for the orders of the customer, up to a page of 100 (AC-26)', () => {
    service.list('c-1').subscribe();
    const req = http.expectOne((r) => r.url === '/api/orders/');
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('customer_id')).toBe('c-1');
    expect(req.request.params.get('page_size')).toBe('100');
    req.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('maps date, total, delivery status and payment status, keeping the server order (AC-26)', () => {
    let history: unknown;
    service.list('c-1').subscribe((h) => (history = h));
    http.expectOne((r) => r.url === '/api/orders/').flush({
      count: 2,
      next: null,
      previous: null,
      results: [
        { id: 'o2', order_date: '2026-10-05', total: '120.50', status: 'DELIVERED', payment_status: 'PARTIAL', code: 'P-2' },
        { id: 'o1', order_date: '2026-09-01', total: '35.00', status: 'CANCELLED', payment_status: 'PENDING', code: 'P-1' },
      ],
    });
    expect(history).toEqual({
      total: 2,
      orders: [
        { id: 'o2', date: '2026-10-05', total: '120.50', status: 'DELIVERED', paymentStatus: 'PARTIAL' },
        { id: 'o1', date: '2026-09-01', total: '35.00', status: 'CANCELLED', paymentStatus: 'PENDING' },
      ],
    });
  });

  it('reports the total even when it exceeds the page (AC-26)', () => {
    let total = 0;
    service.list('c-1').subscribe((h) => (total = h.total));
    http.expectOne((r) => r.url === '/api/orders/').flush({ count: 250, next: 'x', previous: null, results: [] });
    expect(total).toBe(250);
  });

  it('fails with a readable message (AC-26)', () => {
    let error: Error | undefined;
    service.list('c-1').subscribe({ error: (e: Error) => (error = e) });
    http.expectOne((r) => r.url === '/api/orders/').flush('boom', { status: 500, statusText: 'x' });
    expect(error?.message).toBe(HISTORY_ERROR_MESSAGE);
  });
});
