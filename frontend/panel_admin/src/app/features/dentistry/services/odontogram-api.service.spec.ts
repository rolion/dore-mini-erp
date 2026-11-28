import { provideTestTranslations } from '../../../core/i18n/testing';
import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { EvaluationInput } from '../models/odontogram';
import { OdontogramApiService, evaluationError } from './odontogram-api.service';

describe('OdontogramApiService contracts (API-01…API-05)', () => {
  let api: OdontogramApiService;
  let http: HttpTestingController;
  const input: EvaluationInput = { dentition: 'mixed', clinical_date: '2026-11-20', professional_id: null, findings: [], general_findings: [] };
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(OdontogramApiService); http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('reads the catalog', () => {
    let version: string | number | undefined;
    api.catalog().subscribe(catalog => { version = catalog.catalog_version; });
    http.expectOne('/api/dentistry/odontogram/catalog/').flush({ catalog_version: 1 });
    expect(version).toBe(1);
  });
  it('lists evaluations of a patient with a large page', () => {
    api.list('c-1').subscribe();
    const request = http.expectOne(req => req.url === '/api/dentistry/patients/c-1/evaluations/');
    expect(request.request.params.get('page_size')).toBe('100');
    request.flush({ count: 0, results: [], next: null, previous: null });
  });
  it('creates, replaces, discards, confirms and amends', () => {
    api.create('c-1', input).subscribe();
    const create = http.expectOne('/api/dentistry/patients/c-1/evaluations/');
    expect(create.request.method).toBe('POST'); expect(create.request.body).toEqual(input); create.flush({});
    api.update('e-1', input).subscribe();
    const update = http.expectOne('/api/dentistry/evaluations/e-1/');
    expect(update.request.method).toBe('PUT'); update.flush({});
    api.discard('e-1').subscribe();
    const discard = http.expectOne('/api/dentistry/evaluations/e-1/');
    expect(discard.request.method).toBe('DELETE'); discard.flush(null);
    api.confirm('e-1').subscribe();
    const confirm = http.expectOne('/api/dentistry/evaluations/e-1/confirm/');
    expect(confirm.request.method).toBe('POST'); confirm.flush({});
    api.amend('e-1', 'Error de pieza').subscribe();
    const amend = http.expectOne('/api/dentistry/evaluations/e-1/amend/');
    expect(amend.request.body).toEqual({ reason: 'Error de pieza' }); amend.flush({});
  });
  it('turns server errors into messages', () => {
    expect(evaluationError(new HttpErrorResponse({ status: 409, error: { detail: 'Ya existe un borrador.' } }))).toBe('Ya existe un borrador.');
    expect(evaluationError(new HttpErrorResponse({ status: 400, error: { findings: [{ piece: ['Pieza 19 inválida.'] }] } }))).toContain('Pieza 19 inválida.');
    expect(evaluationError(new HttpErrorResponse({ status: 403, error: {} }))).toContain('permiso');
    expect(evaluationError(new HttpErrorResponse({ status: 500 }))).toContain('No se pudo');
  });
});
