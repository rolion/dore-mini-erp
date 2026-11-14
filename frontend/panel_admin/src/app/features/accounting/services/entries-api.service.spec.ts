import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { AccountingApiError } from '../models/accounting';
import { EntryPage } from '../models/entry';
import { makeEntryDto } from '../testing/entry-fixtures';
import { EntriesApiService } from './entries-api.service';

describe('EntriesApiService', () => {
  let service: EntriesApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(EntriesApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('sends only the filters that are set and maps the page, totals and coverage (AC-05, AC-09)', () => {
    let page: EntryPage | undefined;
    service.list({ dateFrom: '2026-11-01', origin: 'SERVICE', method: '', page: 2, pageSize: 20 }).subscribe((p) => (page = p));
    const req = http.expectOne((r) => r.url.endsWith('/accounting/entries/'));
    expect(req.request.params.get('date_from')).toBe('2026-11-01');
    expect(req.request.params.get('origin')).toBe('SERVICE');
    expect(req.request.params.has('method')).toBeFalse();
    expect(req.request.params.get('page')).toBe('2');
    req.flush({
      count: 1,
      results: [makeEntryDto()],
      totals: [{ currency: 'BOB', count: 1, amount: '300.50', by_origin: { PRODUCT: '300.50', SERVICE: '0.00' } }],
      period: { date_from: '2026-11-01', date_to: null },
      coverage: { first_payment_date: '2026-10-05', last_payment_date: '2026-11-01', first_recorded_at: null },
    });
    expect(page?.results[0].accountName).toBe('Caja');
    expect(page?.totals[0].byOrigin.PRODUCT).toBe('300.50');
    expect(page?.coverage.firstPaymentDate).toBe('2026-10-05');
  });

  it('maps a single entry and turns a 404 into an API error', () => {
    let entry: unknown;
    service.get('e-1').subscribe((e) => (entry = e));
    http.expectOne((r) => r.url.endsWith('/accounting/entries/e-1/')).flush(makeEntryDto({ source: { id: 'p-1', document_ref: 'x', receipt_number: 'CB-000001', available: false } }));
    expect(entry).toEqual(jasmine.objectContaining({ id: 'e-1', sourceId: 'p-1', receiptNumber: 'CB-000001', sourceAvailable: false }));

    let error: unknown;
    service.get('nope').subscribe({ error: (e) => (error = e) });
    http.expectOne((r) => r.url.endsWith('/accounting/entries/nope/')).flush({}, { status: 404, statusText: 'Not Found' });
    expect((error as AccountingApiError).status).toBe(404);
  });
});
