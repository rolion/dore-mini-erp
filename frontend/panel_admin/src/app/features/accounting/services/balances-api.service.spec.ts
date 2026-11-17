import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { AccountingApiError } from '../models/accounting';
import { EMPTY_BALANCE_FILTERS } from '../models/balances';
import { makeBalancesDto } from '../testing/balances-fixtures';
import { BalancesApiService } from './balances-api.service';

describe('BalancesApiService', () => {
  let service: BalancesApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(BalancesApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('maps rows and totals and sends no empty filters (AC-01)', () => {
    let result: unknown;
    service.get(EMPTY_BALANCE_FILTERS).subscribe((r) => (result = r));
    const req = http.expectOne((r) => r.url.endsWith('/accounting/balances/'));
    expect(req.request.params.keys()).toEqual([]);
    req.flush(makeBalancesDto());
    const balances = result as { rows: { debitBalance: string; creditBalance: string }[]; totals: { balanced: boolean } };
    expect(balances.rows[0].debitBalance).toBe('700.00');
    expect(balances.rows[1].creditBalance).toBe('700.00');
    expect(balances.totals.balanced).toBeTrue();
  });

  it('sends the active filters as query params (AC-04, AC-05)', () => {
    service.get({ dateFrom: '2026-11-01', dateTo: '2026-11-30', accountClass: 'ASSET', accountId: 'a-1' }).subscribe();
    const req = http.expectOne((r) => r.url.endsWith('/accounting/balances/'));
    expect(req.request.params.get('date_from')).toBe('2026-11-01');
    expect(req.request.params.get('date_to')).toBe('2026-11-30');
    expect(req.request.params.get('account_class')).toBe('ASSET');
    expect(req.request.params.get('account_id')).toBe('a-1');
    req.flush(makeBalancesDto());
  });

  it('turns a server error into an AccountingApiError', () => {
    let error: unknown;
    service.get(EMPTY_BALANCE_FILTERS).subscribe({ error: (e) => (error = e) });
    http.expectOne((r) => r.url.endsWith('/accounting/balances/')).flush({}, { status: 400, statusText: 'Bad' });
    expect(error instanceof AccountingApiError).toBeTrue();
  });
});
