import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../../environments/environment';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { CrmApiError } from '../models/board';
import { CrmTaskDto } from '../models/task';
import { CrmTasksApiService } from './crm-tasks-api.service';

describe('CrmTasksApiService', () => {
  let api: CrmTasksApiService;
  let http: HttpTestingController;
  const base = `${environment.apiUrl}/crm/tasks/`;
  const dto: CrmTaskDto = {
    id: 't-1', title: 'Llamar', related: { type: 'customer', id: 'c-1', name: 'Ana' }, owner: { id: 7, name: 'Ana Admin' },
    due_at: '2026-11-26T15:00:00Z', status: 'pending', is_overdue: false, completed_at: null, created_at: '2026-11-25T10:00:00Z',
  };

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(CrmTasksApiService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('lists with filters and maps the page (API-01)', () => {
    let count = -1;
    let overdue = true;
    api.list({ ownerId: 7, status: 'overdue', customerId: 'c-1', page: 2, pageSize: 10 }).subscribe((p) => {
      count = p.count;
      overdue = p.results[0].isOverdue;
    });
    const req = http.expectOne((r) => r.url === base);
    expect(req.request.params.get('owner_id')).toBe('7');
    expect(req.request.params.get('status')).toBe('overdue');
    expect(req.request.params.get('customer_id')).toBe('c-1');
    expect(req.request.params.get('page_size')).toBe('10');
    req.flush({ count: 1, next: null, previous: null, results: [dto] });
    expect([count, overdue]).toEqual([1, false]);
  });

  it('creates for a customer or an opportunity using the matching key (API-01)', () => {
    api.create({ title: ' Llamar ', dueAt: '2026-11-26T15:00:00Z', related: { type: 'customer', id: 'c-1' }, ownerId: 7 }).subscribe();
    const first = http.expectOne(base);
    expect(first.request.body).toEqual({ title: 'Llamar', due_at: '2026-11-26T15:00:00Z', customer_id: 'c-1', owner_id: 7 });
    first.flush(dto);
    api.create({ title: 'Visita', dueAt: '2026-11-26T15:00:00Z', related: { type: 'opportunity', id: 'o-1' } }).subscribe();
    const second = http.expectOne(base);
    expect(second.request.body).toEqual({ title: 'Visita', due_at: '2026-11-26T15:00:00Z', opportunity_id: 'o-1' });
    second.flush(dto);
  });

  it('patches only the given fields (API-02)', () => {
    api.update('t-1', { title: 'Otro' }).subscribe();
    const req = http.expectOne(`${base}t-1/`);
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ title: 'Otro' });
    req.flush(dto);
  });

  it('completes with an optional activity (API-03)', () => {
    let activityId: string | null = 'x';
    api.complete('t-1', { channel: 'call', outcome: 'contacted', notes: ' ok ' }).subscribe((r) => (activityId = r.activity?.id ?? null));
    const req = http.expectOne(`${base}t-1/complete/`);
    expect(req.request.body).toEqual({ activity: { channel: 'call', outcome: 'contacted', notes: 'ok', occurred_at: null } });
    req.flush({
      ...dto, status: 'done', completed_at: '2026-11-25T12:00:00Z',
      activity: { id: 'a-1', customer_id: 'c-1', opportunity_id: null, task_id: 't-1', actor: { id: 7, name: 'A' }, channel: 'call',
        outcome: 'contacted', notes: 'ok', occurred_at: '2026-11-25T12:00:00Z', created_at: '2026-11-25T12:00:00Z' },
    });
    expect(activityId).toBe('a-1');
    api.complete('t-1').subscribe();
    const bare = http.expectOne(`${base}t-1/complete/`);
    expect(bare.request.body).toEqual({});
    bare.flush({ ...dto, activity: null });
  });

  it('posts cancel, reopen and archive actions (API-03)', () => {
    for (const action of ['cancel', 'reopen', 'archive'] as const) {
      api[action]('t-1').subscribe();
      const req = http.expectOne(`${base}t-1/${action}/`);
      expect(req.request.method).toBe('POST');
      req.flush(dto);
    }
  });

  it('turns a 409 into CrmApiError with the server message and code', () => {
    let error: CrmApiError | undefined;
    api.cancel('t-1').subscribe({ error: (e: CrmApiError) => (error = e) });
    http.expectOne(`${base}t-1/cancel/`).flush({ detail: 'No se puede.', code: 'invalid_task_transition' }, { status: 409, statusText: 'Conflict' });
    expect([error?.status, error?.code, error?.message]).toEqual([409, 'invalid_task_transition', 'No se puede.']);
  });
});
