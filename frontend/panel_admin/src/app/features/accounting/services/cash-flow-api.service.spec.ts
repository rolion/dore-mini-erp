import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { AccountingApiError } from '../models/accounting';
import { CashFlow, CashFlowMovementPage, currentMonthRange, isCashFlowRangeInvalid } from '../models/cash-flow';
import { makeCashFlowDto, makeMovementPageDto } from '../testing/cash-flow-fixtures';
import { CashFlowApiService } from './cash-flow-api.service';

describe('CashFlowApiService', () => {
  let service: CashFlowApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(CashFlowApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('sends the range and maps the summary and per-account transfers (AC-02, AC-04)', () => {
    let result: CashFlow | undefined;
    service.summary('2026-05-01', '2026-05-31').subscribe((r) => (result = r));
    const req = http.expectOne((r) => r.url.endsWith('/accounting/cash-flow/'));
    expect(req.request.params.get('date_from')).toBe('2026-05-01');
    expect(req.request.params.get('date_to')).toBe('2026-05-31');
    req.flush(makeCashFlowDto());
    expect(result?.summary.net).toBe('727.00');
    expect(result?.accounts[0]).toEqual(jasmine.objectContaining({ accountId: 'a-cash', transfersOut: '500.00', closing: '227.00' }));
    expect(result?.accounts[1].transfersIn).toBe('500.00');
  });

  it('sends account, type and page only when set and maps the movements (AC-05, AC-06)', () => {
    let result: CashFlowMovementPage | undefined;
    service.movements({ dateFrom: '2026-05-01', dateTo: '2026-05-31', accountId: 'a-cash', type: 'transfer' }, 2, 20).subscribe((r) => (result = r));
    const req = http.expectOne((r) => r.url.endsWith('/accounting/cash-flow/movements/'));
    expect(req.request.params.get('account_id')).toBe('a-cash');
    expect(req.request.params.get('type')).toBe('transfer');
    expect(req.request.params.get('page')).toBe('2');
    req.flush(makeMovementPageDto());
    expect(result?.results[0]).toEqual(jasmine.objectContaining({ entryId: 'e-1', accountName: 'Caja', amount: '90.00', isReversal: false }));
    expect(result?.totals.transfersOut).toBe('500.00');

    service.movements({ dateFrom: '2026-05-01', dateTo: '2026-05-31', accountId: '', type: '' }, 1, 20).subscribe();
    const bare = http.expectOne((r) => r.url.endsWith('/accounting/cash-flow/movements/'));
    expect(bare.request.params.has('account_id')).toBeFalse();
    expect(bare.request.params.has('type')).toBeFalse();
    bare.flush(makeMovementPageDto());
  });

  it('turns HTTP errors into an AccountingApiError', () => {
    let error: unknown;
    service.summary('2026-05-01', '2026-05-31').subscribe({ error: (e) => (error = e) });
    http.expectOne((r) => r.url.endsWith('/accounting/cash-flow/')).flush({ code: 'module_disabled', detail: 'Módulo no habilitado' }, { status: 403, statusText: 'Forbidden' });
    expect(error).toBeInstanceOf(AccountingApiError);
    expect((error as AccountingApiError).status).toBe(403);
  });

  it('validates the range and defaults to the current month', () => {
    expect(isCashFlowRangeInvalid({ dateFrom: '2026-05-02', dateTo: '2026-05-01' })).toBeTrue();
    expect(isCashFlowRangeInvalid({ dateFrom: '', dateTo: '2026-05-01' })).toBeTrue();
    expect(isCashFlowRangeInvalid({ dateFrom: '2026-05-01', dateTo: '2026-05-01' })).toBeFalse();
    expect(currentMonthRange(new Date(2026, 1, 10))).toEqual({ dateFrom: '2026-02-01', dateTo: '2026-02-28' });
  });
});
