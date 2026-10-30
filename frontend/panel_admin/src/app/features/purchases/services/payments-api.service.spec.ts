import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { Page } from '../../../shared/models/page';
import { Payment, PaymentApiError } from '../models/payment';
import { PaymentsApiService, toPaymentFieldErrors } from './payments-api.service';

const DTO = {
  id: 'pay-1',
  reference: 'PAG-1A2B3C4D',
  amount: '20.00',
  payment_method: 'QR',
  payment_date: '2026-10-30',
  status: 'confirmed',
  user_name: 'ana',
  created_at: '2026-10-30T12:00:00Z',
};

const INPUT = { paymentId: 'id-1', amount: '20.00', paymentMethod: 'QR' as const, paymentDate: '2026-10-30' };

describe('PaymentsApiService', () => {
  let service: PaymentsApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(PaymentsApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lists the payments of a purchase mapping snake_case (AC-10)', () => {
    let page: Page<Payment> | undefined;
    service.list('c-1').subscribe((result) => (page = result));
    http
      .expectOne((r) => r.method === 'GET' && r.url.endsWith('/purchases/c-1/payments/'))
      .flush({ count: 1, next: null, previous: null, results: [DTO] });
    expect(page?.results[0]).toEqual({
      id: 'pay-1',
      reference: 'PAG-1A2B3C4D',
      amount: '20.00',
      paymentMethod: 'QR',
      paymentDate: '2026-10-30',
      status: 'confirmed',
      userName: 'ana',
      createdAt: '2026-10-30T12:00:00Z',
    });
  });

  it('sends the amount as text with the idempotency id (AC-01, AC-18)', () => {
    let payment: Payment | undefined;
    service.create('c-1', INPUT).subscribe((p) => (payment = p));
    const req = http.expectOne((r) => r.method === 'POST' && r.url.endsWith('/purchases/c-1/payments/'));
    expect(req.request.body).toEqual({
      payment_id: 'id-1',
      amount: '20.00',
      payment_method: 'QR',
      payment_date: '2026-10-30',
    });
    expect(typeof (req.request.body as { amount: unknown }).amount).toBe('string');
    req.flush(DTO, { status: 201, statusText: 'Created' });
    expect(payment?.reference).toBe('PAG-1A2B3C4D');
  });

  it('maps field errors of a 400 (AC-03, AC-04)', () => {
    let error: PaymentApiError | undefined;
    service.create('c-1', INPUT).subscribe({ error: (e: PaymentApiError) => (error = e) });
    http.expectOne((r) => r.method === 'POST').flush(
      {
        amount: ['El monto no puede superar el saldo pendiente (10.00).'],
        payment_method: ['El método de pago es obligatorio.'],
        payment_date: ['La fecha del pago no puede ser futura.'],
      },
      { status: 400, statusText: 'Bad Request' },
    );
    expect(error?.status).toBe(400);
    expect(error?.fieldErrors).toEqual({
      amount: 'El monto no puede superar el saldo pendiente (10.00).',
      paymentMethod: 'El método de pago es obligatorio.',
      paymentDate: 'La fecha del pago no puede ser futura.',
    });
  });

  it('maps 409, 404 and network errors (AC-05)', () => {
    const errors: PaymentApiError[] = [];
    const run = (status: number, body: Record<string, unknown> | null): void => {
      service.create('c-1', INPUT).subscribe({ error: (e: PaymentApiError) => errors.push(e) });
      http.expectOne((r) => r.method === 'POST').flush(body, { status, statusText: 'x' });
    };
    run(409, { detail: 'Solo una compra confirmada admite pagos.' });
    run(404, { detail: 'x' });
    run(0, null);
    expect(errors.map((e) => e.status)).toEqual([409, 404, 0]);
    expect(errors[0].message).toBe('Solo una compra confirmada admite pagos.');
    expect(errors[1].message).toContain('No se encontró');
  });

  it('ignores a non-object error body', () => {
    expect(toPaymentFieldErrors(null)).toEqual({});
  });
});
