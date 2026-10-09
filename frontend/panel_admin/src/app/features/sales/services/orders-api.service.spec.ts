import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { OrderApiError, OrderRuleError } from '../models/order';
import { makeOrder, makeOrderDto, makeSummary } from '../testing/order-fixtures';
import {
  GENERIC_ERROR_MESSAGE,
  NETWORK_ERROR_MESSAGE,
  NOT_FOUND_MESSAGE,
  OrdersApiService,
  VALIDATION_ERROR_MESSAGE,
} from './orders-api.service';

describe('OrdersApiService', () => {
  let service: OrdersApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(OrdersApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  describe('list', () => {
    it('sends no params by default and maps summaries (AC-16)', () => {
      let result: unknown;
      service.list().subscribe((page) => (result = page));
      const req = http.expectOne('/api/orders/');
      expect(req.request.method).toBe('GET');
      expect(req.request.params.keys()).toEqual([]);
      req.flush({
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 'o-1',
            code: 'P-1A2B3C4D',
            customer: { id: 'c-1', name: 'Ana Pérez' },
            sales_channel: 'WHATSAPP',
            order_date: '2026-10-01',
            expected_delivery_date: '2026-10-05',
            status: 'NEW',
            payment_status: 'PENDING',
            total: '70.00',
            paid_total: '0.00',
            balance: '70.00',
          },
        ],
      });
      expect(result).toEqual({ count: 1, next: null, previous: null, results: [makeSummary()] });
    });

    it('translates every filter to its query param (AC-16, AC-23)', () => {
      service
        .list({
          status: ['NEW', 'READY'],
          paymentStatus: ['PENDING', 'PARTIAL'],
          salesChannel: 'FAIR',
          customerId: 'c-9',
          dateField: 'expected_delivery_date',
          dateFrom: '2026-10-01',
          dateTo: '2026-10-31',
          hasBalance: true,
          ordering: 'expected_delivery_date',
          page: 2,
          pageSize: 10,
        })
        .subscribe();
      const req = http.expectOne((r) => r.url === '/api/orders/');
      const params = req.request.params;
      expect(params.get('status')).toBe('NEW,READY');
      expect(params.get('payment_status')).toBe('PENDING,PARTIAL');
      expect(params.get('sales_channel')).toBe('FAIR');
      expect(params.get('customer_id')).toBe('c-9');
      expect(params.get('date_field')).toBe('expected_delivery_date');
      expect(params.get('date_from')).toBe('2026-10-01');
      expect(params.get('date_to')).toBe('2026-10-31');
      expect(params.get('has_balance')).toBe('true');
      expect(params.get('ordering')).toBe('expected_delivery_date');
      expect(params.get('page')).toBe('2');
      expect(params.get('page_size')).toBe('10');
      req.flush({ count: 0, next: null, previous: null, results: [] });
    });

    it('sends has_balance=false when asked and omits empty lists (AC-16)', () => {
      service.list({ status: [], hasBalance: false }).subscribe();
      const req = http.expectOne((r) => r.url === '/api/orders/');
      expect(req.request.params.has('status')).toBeFalse();
      expect(req.request.params.get('has_balance')).toBe('false');
      req.flush({ count: 0, next: null, previous: null, results: [] });
    });
  });

  describe('order resource', () => {
    it('maps the detail to the camelCase model, keeping amounts as text (AC-17)', () => {
      let order: unknown;
      service.get('o-1').subscribe((o) => (order = o));
      const req = http.expectOne('/api/orders/o-1/');
      expect(req.request.method).toBe('GET');
      req.flush(makeOrderDto());
      expect(order).toEqual(makeOrder());
      const typed = order as { total: unknown; items: { unitPrice: unknown }[] };
      expect(typeof typed.total).toBe('string');
      expect(typeof typed.items[0].unitPrice).toBe('string');
    });

    it('creates with snake_case body and null customer (AC-24)', () => {
      service
        .create({
          customerId: null,
          salesChannel: 'STORE',
          orderDate: '2026-10-01',
          expectedDeliveryDate: null,
          notes: 'n',
        })
        .subscribe();
      const req = http.expectOne('/api/orders/');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({
        customer_id: null,
        sales_channel: 'STORE',
        order_date: '2026-10-01',
        expected_delivery_date: null,
        notes: 'n',
      });
      req.flush(makeOrderDto());
    });

    it('patches only the given fields (AC-24)', () => {
      service.update('o-1', { notes: 'x', expectedDeliveryDate: null }).subscribe();
      const req = http.expectOne('/api/orders/o-1/');
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body).toEqual({ notes: 'x', expected_delivery_date: null });
      req.flush(makeOrderDto());
    });
  });

  describe('actions', () => {
    const cases: [string, () => void, string, string, unknown][] = [
      ['addItem', () => service.addItem('o-1', 'p-1', 2).subscribe(), 'POST', '/api/orders/o-1/items/', { product_id: 'p-1', quantity: 2 }],
      ['changeItemQuantity', () => service.changeItemQuantity('o-1', 'i-1', 5).subscribe(), 'PATCH', '/api/orders/o-1/items/i-1/', { quantity: 5 }],
      ['removeItem', () => service.removeItem('o-1', 'i-1').subscribe(), 'DELETE', '/api/orders/o-1/items/i-1/', null],
      ['applyDiscount', () => service.applyDiscount('o-1', '10.00').subscribe(), 'POST', '/api/orders/o-1/discount/', { discount: '10.00' }],
      ['prepare', () => service.prepare('o-1').subscribe(), 'POST', '/api/orders/o-1/prepare/', {}],
      ['ready', () => service.ready('o-1').subscribe(), 'POST', '/api/orders/o-1/ready/', {}],
      ['deliver', () => service.deliver('o-1').subscribe(), 'POST', '/api/orders/o-1/deliver/', {}],
      ['deliver with date', () => service.deliver('o-1', '2026-10-03').subscribe(), 'POST', '/api/orders/o-1/deliver/', { delivered_date: '2026-10-03' }],
      ['cancel', () => service.cancel('o-1', 'No lo quiere').subscribe(), 'POST', '/api/orders/o-1/cancel/', { reason: 'No lo quiere' }],
      [
        'registerPayment',
        () =>
          service
            .registerPayment('o-1', { amount: '20.00', paymentMethod: 'QR', paymentDate: '2026-10-02', reference: 'r' })
            .subscribe(),
        'POST',
        '/api/orders/o-1/payments/',
        { amount: '20.00', payment_method: 'QR', payment_date: '2026-10-02', reference: 'r' },
      ],
    ];

    for (const [name, call, method, url, body] of cases) {
      it(`${name}: ${method} ${url} (AC-25)`, () => {
        call();
        const req = http.expectOne(url);
        expect(req.request.method).toBe(method);
        expect(req.request.body).toEqual(body);
        req.flush(makeOrderDto());
      });
    }
  });

  describe('errors', () => {
    function failWith(status: number, body: object | string): OrderApiError {
      let error: OrderApiError | undefined;
      service.get('o-1').subscribe({ error: (e: OrderApiError) => (error = e) });
      http.expectOne('/api/orders/o-1/').flush(body, { status, statusText: 'x' });
      return error as OrderApiError;
    }

    it('maps 400 to field errors in camelCase and ignores unknown keys (AC-24)', () => {
      const error = failWith(400, { sales_channel: ['Obligatorio'], expected_delivery_date: ['Antes'], otro: ['x'] });
      expect(error.status).toBe(400);
      expect(error.message).toBe(VALIDATION_ERROR_MESSAGE);
      expect(error.fieldErrors).toEqual({ salesChannel: ['Obligatorio'], expectedDeliveryDate: ['Antes'] });
    });

    it('maps 409 with a code to OrderRuleError carrying the server message (AC-25)', () => {
      const error = failWith(409, { code: 'invalid_transition', detail: 'Esa acción no está permitida.' });
      expect(error instanceof OrderRuleError).toBeTrue();
      expect((error as OrderRuleError).code).toBe('invalid_transition');
      expect(error.message).toBe('Esa acción no está permitida.');
      expect(error.status).toBe(409);
    });

    it('maps a 409 without code to the generic error', () => {
      const error = failWith(409, 'raro');
      expect(error instanceof OrderRuleError).toBeFalse();
      expect(error.message).toBe(GENERIC_ERROR_MESSAGE);
    });

    it('maps 404 using the server detail or a default (EDGE-12)', () => {
      expect(failWith(404, { detail: 'Pedido no encontrado.' }).message).toBe('Pedido no encontrado.');
      expect(failWith(404, 'html').message).toBe(NOT_FOUND_MESSAGE);
    });

    it('maps network failures and unexpected statuses', () => {
      let error: OrderApiError | undefined;
      service.get('o-1').subscribe({ error: (e: OrderApiError) => (error = e) });
      http.expectOne('/api/orders/o-1/').error(new ProgressEvent('error'));
      expect(error?.status).toBe(0);
      expect(error?.message).toBe(NETWORK_ERROR_MESSAGE);
      expect(failWith(500, {}).message).toBe(GENERIC_ERROR_MESSAGE);
    });
  });
});
