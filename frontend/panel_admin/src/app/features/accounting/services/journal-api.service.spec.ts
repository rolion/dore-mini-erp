import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { AccountingApiError } from '../models/accounting';
import { makeJournalDetailDto, makeJournalRowDto } from '../testing/journal-fixtures';
import { JournalApiService } from './journal-api.service';

describe('JournalApiService', () => {
  let service: JournalApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(JournalApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('sends only the filters that are set and maps the page (AC-03)', () => {
    let count = -1;
    service.list({ dateFrom: '2026-05-01', accountId: '', source: 'MANUAL', page: 2, pageSize: 20 }).subscribe((p) => (count = p.count));
    const req = http.expectOne((r) => r.url.endsWith('/accounting/journal-entries/'));
    expect(req.request.params.get('date_from')).toBe('2026-05-01');
    expect(req.request.params.get('source')).toBe('MANUAL');
    expect(req.request.params.has('account_id')).toBeFalse();
    expect(req.request.params.get('page')).toBe('2');
    req.flush({ count: 1, results: [makeJournalRowDto()] });
    expect(count).toBe(1);
  });

  it('posts a manual entry and maps the detail (AC-01)', () => {
    let total = '';
    service.create({ accounting_date: '2026-05-10', description: 'Servicio', lines: [] }).subscribe((e) => (total = e.totalDebit));
    const req = http.expectOne((r) => r.url.endsWith('/accounting/journal-entries/'));
    expect(req.request.method).toBe('POST');
    req.flush(makeJournalDetailDto(), { status: 201, statusText: 'Created' });
    expect(total).toBe('500.00');
  });

  it('keeps the server messages of a 400 by field (AC-02)', () => {
    let error: AccountingApiError | undefined;
    service.create({ accounting_date: '2026-05-10', description: 'x', lines: [] }).subscribe({ error: (e: AccountingApiError) => (error = e) });
    http.expectOne((r) => r.url.endsWith('/accounting/journal-entries/')).flush({ lines: ['El asiento no cuadra'] }, { status: 400, statusText: 'Bad Request' });
    expect(error?.fieldErrors['lines']).toEqual(['El asiento no cuadra']);
  });

  it('reverses with date and reason (AC-07)', () => {
    service.reverse('j-1', '2026-05-12', 'Error').subscribe();
    const req = http.expectOne((r) => r.url.endsWith('/accounting/journal-entries/j-1/reverse/'));
    expect(req.request.body).toEqual({ reversal_date: '2026-05-12', reason: 'Error' });
    req.flush(makeJournalDetailDto({ reverses_id: 'j-1', reversal_reason: 'Error', can_reverse: false }), { status: 201, statusText: 'Created' });
  });

  it('gets one entry', () => {
    service.get('j-1').subscribe();
    http.expectOne((r) => r.url.endsWith('/accounting/journal-entries/j-1/')).flush(makeJournalDetailDto());
  });
});
