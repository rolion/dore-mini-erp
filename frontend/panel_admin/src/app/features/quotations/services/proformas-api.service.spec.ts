import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { previewSubtotal, ProformaFailure, ProformaInput } from '../models/proforma';
import { ProformasApiService } from './proformas-api.service';

describe('ProformasApiService', () => {
  let service: ProformasApiService;
  let http: HttpTestingController;
  const input: ProformaInput = {
    customer_id: 'c1', date: '2026-11-03', valid_until: null, notes: '',
    lines: [{ service_id: 's1', quantity: '1' }],
  };

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), ...provideTestTranslations()] });
    service = TestBed.inject(ProformasApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('sends filters as query params and skips empty ones', () => {
    service.list({ customer: 'rosa', status: '', from: '2026-11-01', page: 2 }).subscribe();
    const req = http.expectOne(r => r.url.endsWith('/quotations/proformas/'));
    expect(req.request.params.get('customer')).toBe('rosa');
    expect(req.request.params.get('page')).toBe('2');
    expect(req.request.params.has('status')).toBeFalse();
    req.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('posts, puts and runs actions on the proformas endpoint', () => {
    service.create(input).subscribe();
    http.expectOne(r => r.method === 'POST' && r.url.endsWith('/quotations/proformas/')).flush({});
    service.update('p1', input).subscribe();
    http.expectOne(r => r.method === 'PUT' && r.url.endsWith('/proformas/p1/')).flush({});
    service.present('p1').subscribe();
    http.expectOne(r => r.method === 'POST' && r.url.endsWith('/proformas/p1/present/')).flush({});
    service.newVersion('p1').subscribe();
    http.expectOne(r => r.method === 'POST' && r.url.endsWith('/proformas/p1/new-version/')).flush({});
  });

  it('maps 400 line errors by position and keeps header errors', () => {
    let failure: ProformaFailure | undefined;
    service.create(input).subscribe({ error: (error: ProformaFailure) => failure = error });
    http.expectOne(r => r.method === 'POST').flush(
      { customer_id: ['The customer is inactive.'], lines: [{}, { quantity: ['Server message in any language.'] }] },
      { status: 400, statusText: 'Bad Request' });
    expect(failure?.fields['customer_id']).toBe('Selecciona un cliente activo.');
    expect(failure?.lines[1]['quantity']).toContain('cantidad mayor que cero');
    expect(failure?.lines[0]).toEqual({});
  });

  it('maps 409 as conflict and tells apart a price 403 from a disabled module', () => {
    let failure: ProformaFailure | undefined;
    service.present('p1').subscribe({ error: (error: ProformaFailure) => failure = error });
    http.expectOne(r => r.method === 'POST').flush({ detail: 'Server detail in another language.' },
      { status: 409, statusText: 'Conflict' });
    expect(failure?.conflict).toBeTrue();
    service.create(input).subscribe({ error: (error: ProformaFailure) => failure = error });
    http.expectOne(r => r.method === 'POST').flush({ detail: 'x' }, { status: 403, statusText: 'Forbidden' });
    expect(failure?.message).toBe('No tienes permiso para editar precios.');
    service.create(input).subscribe({ error: (error: ProformaFailure) => failure = error });
    http.expectOne(r => r.method === 'POST').flush({ code: 'module_disabled' }, { status: 403, statusText: 'Forbidden' });
    expect(failure?.message).toContain('módulo requerido');
  });
});

describe('previewSubtotal', () => {
  it('rounds to two decimals half-up', () => {
    expect(previewSubtotal('1', '100')).toBe(100);
    expect(previewSubtotal('1.5', '0.15')).toBe(0.23);
    expect(previewSubtotal('abc', '1')).toBe(0);
  });
});
