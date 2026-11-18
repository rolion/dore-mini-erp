import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { AccountingApiError } from '../models/accounting';
import { FiscalPeriodsApiService } from './fiscal-periods-api.service';

const dto = { id: 'p1', name: '2026', start_date: '2026-01-01', end_date: '2026-12-31', status: 'CLOSED', closed_by_name: 'Ana' };

describe('FiscalPeriodsApiService', () => {
  let service: FiscalPeriodsApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(FiscalPeriodsApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('maps the list (AC-01)', () => {
    let result: unknown;
    service.list().subscribe((r) => (result = r));
    http.expectOne((r) => r.url.endsWith('/accounting/fiscal-periods/')).flush([dto]);
    expect(result).toEqual([{ id: 'p1', name: '2026', startDate: '2026-01-01', endDate: '2026-12-31', status: 'CLOSED', isOpen: false, closedByName: 'Ana' }]);
  });

  it('sends snake_case on create and update', () => {
    service.create({ name: 'x', startDate: '2026-01-01', endDate: '2026-02-01' }).subscribe();
    const create = http.expectOne((r) => r.method === 'POST' && r.url.endsWith('/fiscal-periods/'));
    expect(create.request.body).toEqual({ name: 'x', start_date: '2026-01-01', end_date: '2026-02-01' });
    create.flush(dto);
    service.update('p1', { name: 'y', startDate: '2026-01-01', endDate: '2026-02-01' }).subscribe();
    const update = http.expectOne((r) => r.method === 'PATCH' && r.url.endsWith('/fiscal-periods/p1/'));
    expect(update.request.body.name).toBe('y');
    update.flush(dto);
  });

  it('closes and reopens through the action endpoints (AC-05)', () => {
    service.close('p1').subscribe();
    http.expectOne((r) => r.method === 'POST' && r.url.endsWith('/fiscal-periods/p1/close/')).flush(dto);
    service.reopen('p1').subscribe();
    http.expectOne((r) => r.method === 'POST' && r.url.endsWith('/fiscal-periods/p1/reopen/')).flush(dto);
  });

  it('maps 400 date errors to form fields and 409 to the server message', () => {
    let error: AccountingApiError | undefined;
    service.create({ name: 'x', startDate: '2026-02-01', endDate: '2026-01-01' }).subscribe({ error: (e) => (error = e) });
    http.expectOne((r) => r.method === 'POST').flush({ end_date: ['Fin anterior.'] }, { status: 400, statusText: 'Bad Request' });
    expect(error?.fieldErrors['endDate']).toEqual(['Fin anterior.']);
    service.close('p1').subscribe({ error: (e) => (error = e) });
    http.expectOne((r) => r.url.endsWith('/close/')).flush({ detail: 'Ya está cerrado.', code: 'period_invalid_state' }, { status: 409, statusText: 'Conflict' });
    expect([error?.status, error?.message, error?.code]).toEqual([409, 'Ya está cerrado.', 'period_invalid_state']);
  });
});
