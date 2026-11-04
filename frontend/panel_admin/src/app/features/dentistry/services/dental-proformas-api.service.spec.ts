import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { DentalProformaFailure, DentalProformaInput } from '../models/dental-proforma';
import { DentalProformasApiService } from './dental-proformas-api.service';

describe('DentalProformasApiService', () => {
  let service: DentalProformasApiService;
  let http: HttpTestingController;
  const input: DentalProformaInput = {
    date: '2026-11-04', valid_until: null, notes: '',
    lines: [{ service_id: 's1', quantity: '1', dental_piece: '18' }],
  };

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), ...provideTestTranslations()] });
    service = TestBed.inject(DentalProformasApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lists the proformas of one patient with the page and skips empty filters', () => {
    service.listForPatient('c-1', { page: 2, status: '' }).subscribe();
    const req = http.expectOne(r => r.url.endsWith('/dentistry/patients/c-1/proformas/'));
    expect(req.request.params.get('page')).toBe('2');
    expect(req.request.params.has('status')).toBeFalse();
    req.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('creates under the patient and sends the dental piece of each line', () => {
    service.create('c-1', input).subscribe();
    const req = http.expectOne(r => r.method === 'POST' && r.url.endsWith('/dentistry/patients/c-1/proformas/'));
    expect(req.request.body.lines[0].dental_piece).toBe('18');
    expect('customer_id' in req.request.body).toBeFalse();
    req.flush({});
  });

  it('puts, gets and runs actions on the proformas endpoint', () => {
    service.update('p1', input).subscribe();
    http.expectOne(r => r.method === 'PUT' && r.url.endsWith('/dentistry/proformas/p1/')).flush({});
    service.get('p1').subscribe();
    http.expectOne(r => r.method === 'GET' && r.url.endsWith('/dentistry/proformas/p1/')).flush({});
    service.present('p1').subscribe();
    http.expectOne(r => r.method === 'POST' && r.url.endsWith('/proformas/p1/present/')).flush({});
    service.newVersion('p1').subscribe();
    http.expectOne(r => r.method === 'POST' && r.url.endsWith('/proformas/p1/new-version/')).flush({});
  });

  it('translates field and line errors, including the dental piece, instead of showing server text', () => {
    let failure: DentalProformaFailure | undefined;
    service.create('c-1', input).subscribe({ error: (error: DentalProformaFailure) => failure = error });
    http.expectOne(r => r.method === 'POST').flush(
      { customer_id: ['server text'], lines: [{}, { dental_piece: ['server text'], quantity: ['server text'] }] },
      { status: 400, statusText: 'Bad Request' });
    expect(failure?.fields['customer_id']).toContain('inactivo');
    expect(failure?.lines[0]).toEqual({});
    expect(failure?.lines[1]['dental_piece']).toContain('20 caracteres');
    expect(failure?.lines[1]['quantity']).toContain('cantidad mayor que cero');
  });

  it('maps 409 as conflict, 404 and the two kinds of 403', () => {
    let failure: DentalProformaFailure | undefined;
    const run = (status: number, body: object) => {
      service.present('p1').subscribe({ error: (error: DentalProformaFailure) => failure = error });
      http.expectOne(r => r.method === 'POST').flush(body, { status, statusText: 'x' });
    };
    run(409, { detail: 'x' });
    expect(failure?.conflict).toBeTrue();
    expect(failure?.message).toContain('archivado');
    run(404, {});
    expect(failure?.message).toContain('no encontrado');
    run(403, { detail: 'x' });
    expect(failure?.message).toBe('No tienes permiso para editar precios.');
    run(403, { code: 'module_disabled' });
    expect(failure?.message).toContain('módulo requerido');
  });
});
