import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../../environments/environment';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { CrmApiError } from '../models/board';
import { CrmActivitiesApiService } from './crm-activities-api.service';

describe('CrmActivitiesApiService', () => {
  let api: CrmActivitiesApiService;
  let http: HttpTestingController;
  const base = `${environment.apiUrl}/crm/activities/`;
  const dto = {
    id: 'a-1', customer_id: null, opportunity_id: 'o-1', task_id: null, actor: { id: 7, name: 'Ana' }, channel: 'whatsapp',
    outcome: '', notes: 'Solo nota', occurred_at: '2026-11-25T14:00:00Z', created_at: '2026-11-25T14:00:00Z',
  };

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(CrmActivitiesApiService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('lists the history of one entity (API-04)', () => {
    let first = '';
    api.list({ type: 'opportunity', id: 'o-1' }, 2, 5).subscribe((p) => (first = p.results[0].notes));
    const req = http.expectOne((r) => r.url === base);
    expect(req.request.params.get('opportunity_id')).toBe('o-1');
    expect(req.request.params.has('customer_id')).toBeFalse();
    expect(req.request.params.get('page')).toBe('2');
    req.flush({ count: 1, next: null, previous: null, results: [dto] });
    expect(first).toBe('Solo nota');
  });

  it('creates an activity with a null outcome when none is chosen (API-04)', () => {
    api.create({ related: { type: 'customer', id: 'c-1' }, channel: 'call', outcome: '', notes: ' Hola ' }).subscribe();
    const req = http.expectOne(base);
    expect(req.request.body).toEqual({ customer_id: 'c-1', channel: 'call', outcome: null, notes: 'Hola', occurred_at: null });
    req.flush(dto);
  });

  it('surfaces field errors from a 400', () => {
    let error: CrmApiError | undefined;
    api.create({ related: { type: 'customer', id: 'c-1' }, channel: 'call', outcome: '', notes: '' }).subscribe({ error: (e: CrmApiError) => (error = e) });
    http.expectOne(base).flush({ notes: ['Indica un resultado o escribe una nota.'] }, { status: 400, statusText: 'Bad Request' });
    expect(error?.fieldErrors['notes']).toBe('Indica un resultado o escribe una nota.');
  });
});
