import { provideTestTranslations } from '../../../core/i18n/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../../environments/environment';
import { CrmApiError } from '../models/board';
import { CrmLeadConversion, CrmLeadDto, CrmLeadPage } from '../models/lead';
import { CrmLeadsApiService } from './crm-leads-api.service';

describe('CrmLeadsApiService', () => {
  let api: CrmLeadsApiService;
  let http: HttpTestingController;
  const base = `${environment.apiUrl}/crm/leads/`;
  const dto: CrmLeadDto = {
    id: 'l-1', name: 'Carla', phone: '76543210', normalized_phone: '+59176543210', email: 'c@x.com',
    converted_customer_id: null, created_at: '2026-11-20T10:00:00Z',
  };

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(CrmLeadsApiService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('lists leads with search, converted filter and pagination (API-01)', () => {
    let page: CrmLeadPage | undefined;
    api.list({ search: 'car', converted: false, page: 2, pageSize: 10 }).subscribe((p) => (page = p));
    const req = http.expectOne((r) => r.url === base);
    expect(req.request.params.get('search')).toBe('car');
    expect(req.request.params.get('converted')).toBe('false');
    expect(req.request.params.get('page')).toBe('2');
    expect(req.request.params.get('page_size')).toBe('10');
    req.flush({ count: 1, next: null, previous: null, results: [dto] });
    expect(page).toEqual({ count: 1, results: [{
      id: 'l-1', name: 'Carla', phone: '76543210', normalizedPhone: '+59176543210', email: 'c@x.com',
      convertedCustomerId: null, createdAt: '2026-11-20T10:00:00Z',
    }] });
  });

  it('omits empty filters', () => {
    api.list().subscribe();
    const req = http.expectOne(base);
    expect(req.request.params.keys()).toEqual([]);
    req.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('creates and edits a lead with the expected body', () => {
    api.create({ name: 'Carla', phone: '7654', email: '' }).subscribe();
    const create = http.expectOne(base);
    expect(create.request.method).toBe('POST');
    expect(create.request.body).toEqual({ name: 'Carla', phone: '7654', email: '' });
    create.flush(dto);
    api.update('l-1', { name: 'Carla R.' }).subscribe();
    const patch = http.expectOne(`${base}l-1/`);
    expect(patch.request.method).toBe('PATCH');
    expect(patch.request.body).toEqual({ name: 'Carla R.' });
    patch.flush(dto);
  });

  it('converts a lead, optionally to a chosen customer (API-02)', () => {
    let result: CrmLeadConversion | undefined;
    api.convert('l-1').subscribe((r) => (result = r));
    const first = http.expectOne(`${base}l-1/convert/`);
    expect(first.request.method).toBe('POST');
    expect(first.request.body).toEqual({});
    first.flush({ lead: { ...dto, converted_customer_id: 'c-1' }, customer: { id: 'c-1', name: 'Carla', phone: '+591' }, created: true });
    expect(result?.created).toBeTrue();
    expect(result?.lead.convertedCustomerId).toBe('c-1');
    api.convert('l-1', 'c-2').subscribe();
    const chosen = http.expectOne(`${base}l-1/convert/`);
    expect(chosen.request.body).toEqual({ customer_id: 'c-2' });
    chosen.flush({ lead: dto, customer: { id: 'c-2', name: 'X', phone: '' }, created: false });
  });

  it('exposes the candidates of a 409 multiple_customer_matches and 400 field errors', () => {
    const errors: CrmApiError[] = [];
    api.convert('l-1').subscribe({ error: (e: CrmApiError) => errors.push(e) });
    http.expectOne(`${base}l-1/convert/`).flush(
      { detail: 'Varios clientes.', code: 'multiple_customer_matches', candidates: [{ id: 'c-1', name: 'A', phone: '1' }, { id: 'c-2', name: 'B', phone: '1' }] },
      { status: 409, statusText: 'Conflict' });
    api.create({ name: '', phone: '', email: 'x' }).subscribe({ error: (e: CrmApiError) => errors.push(e) });
    http.expectOne(base).flush({ name: ['Obligatorio.'], email: ['Correo inválido.'] }, { status: 400, statusText: 'Bad Request' });
    expect([errors[0].status, errors[0].code, errors[0].message]).toEqual([409, 'multiple_customer_matches', 'Varios clientes.']);
    expect(errors[0].candidates.map((c) => c.id)).toEqual(['c-1', 'c-2']);
    expect(errors[1].fieldErrors['name']).toBe('Obligatorio.');
    expect(errors[1].fieldErrors['email']).toBe('Correo inválido.');
  });
});
