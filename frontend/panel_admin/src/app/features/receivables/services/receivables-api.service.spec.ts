import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { PaymentInput, ReceivableFailure } from '../models/receivable';
import { ReceivablesApiService } from './receivables-api.service';

describe('ReceivablesApiService', () => {
  let service: ReceivablesApiService;
  let http: HttpTestingController;
  const input: PaymentInput = {
    idempotency_key: 'k1', amount: '100.00', payment_method: 'CASH', payment_date: null, reference: '',
    allocations: [{ line_id: 'l1', amount: '100.00' }],
  };

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), ...provideTestTranslations()] });
    service = TestBed.inject(ReceivablesApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lista con filtros y omite los vacíos', () => {
    service.list({ customer_id: 'c1', status: '', date_from: '2026-11-01', page: 2 }).subscribe();
    const request = http.expectOne((req) => req.url.endsWith('/receivables/obligations/'));
    expect(request.request.params.get('customer_id')).toBe('c1');
    expect(request.request.params.has('status')).toBeFalse();
    expect(request.request.params.get('page')).toBe('2');
    request.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('registra el pago con la clave de idempotencia en el cuerpo', () => {
    service.pay('dental', 'ODO-000001', input).subscribe();
    const request = http.expectOne((req) => req.url.endsWith('/receivables/commitments/dental/ODO-000001/payments/'));
    expect(request.request.method).toBe('POST');
    expect(request.request.body.idempotency_key).toBe('k1');
    request.flush({});
  });

  it('traduce 400, 409, 404 y 403 a fallos con mensaje y campos', () => {
    const failures: ReceivableFailure[] = [];
    const run = (status: number, body: object) => {
      service.pay('quotation', 'PRO-000001', input).subscribe({ error: (f: ReceivableFailure) => failures.push(f) });
      http.expectOne((req) => req.url.includes('/payments/')).flush(body, { status, statusText: 'x' });
    };
    run(400, { amount: ['x'], allocations: ['y'] });
    run(409, { detail: 'x' });
    run(404, {});
    run(403, { code: 'module_disabled' });
    expect(Object.keys(failures[0].fields)).toEqual(['amount', 'allocations']);
    expect(failures[1].conflict).toBeTrue();
    expect(failures.every((failure) => failure.message.length > 0)).toBeTrue();
  });
});
