import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { AccountingApiError } from '../models/accounting';
import { EMPTY_BALANCE_SHEET_FILTERS } from '../models/balance-sheet';
import { makeBalanceSheetDto } from '../testing/balance-sheet-fixtures';
import { BalanceSheetApiService } from './balance-sheet-api.service';

describe('BalanceSheetApiService', () => {
  let service: BalanceSheetApiService;
  let http: HttpTestingController;
  const isUrl = (r: { url: string }) => r.url.endsWith('/accounting/balance-sheet/');

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(BalanceSheetApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('maps the response and sends no empty filters', () => {
    let totals = '';
    service.get(EMPTY_BALANCE_SHEET_FILTERS).subscribe((r) => (totals = r.totals.assets));
    const req = http.expectOne(isUrl);
    expect(req.request.params.keys()).toEqual([]);
    req.flush(makeBalanceSheetDto());
    expect(totals).toBe('1500.00');
  });

  it('sends the dates as query params (AC-02, AC-03)', () => {
    service.get({ dateFrom: '2026-01-01', dateTo: '2026-03-31' }).subscribe();
    const req = http.expectOne(isUrl);
    expect(req.request.params.get('date_from')).toBe('2026-01-01');
    expect(req.request.params.get('date_to')).toBe('2026-03-31');
    req.flush(makeBalanceSheetDto());
  });

  it('turns a server error into an AccountingApiError', () => {
    let error: unknown;
    service.get(EMPTY_BALANCE_SHEET_FILTERS).subscribe({ error: (e) => (error = e) });
    http.expectOne(isUrl).flush({}, { status: 400, statusText: 'Bad' });
    expect(error instanceof AccountingApiError).toBeTrue();
  });
});
