import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { AccountingApiError } from '../models/accounting';
import { makeIncomeExpenseDto } from '../testing/income-expense-fixtures';
import { IncomeExpenseApiService } from './income-expense-api.service';

describe('IncomeExpenseApiService', () => {
  let service: IncomeExpenseApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(IncomeExpenseApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('sends no params by default and maps the report (AC-04)', () => {
    let result: unknown;
    service.get({ periodId: '', months: [] }).subscribe((r) => (result = r));
    const req = http.expectOne((r) => r.url.endsWith('/accounting/income-expense/'));
    expect(req.request.params.keys()).toEqual([]);
    req.flush(makeIncomeExpenseDto());
    expect((result as { months: unknown[] }).months.length).toBe(3);
  });

  it('sends the period and the selected months (AC-05)', () => {
    service.get({ periodId: 'p-1', months: ['2026-01', '2026-03'] }).subscribe();
    const req = http.expectOne((r) => r.url.endsWith('/accounting/income-expense/'));
    expect(req.request.params.get('period_id')).toBe('p-1');
    expect(req.request.params.get('months')).toBe('2026-01,2026-03');
    req.flush(makeIncomeExpenseDto());
  });

  it('turns a server error into an AccountingApiError', () => {
    let error: unknown;
    service.get({ periodId: '', months: [] }).subscribe({ error: (e) => (error = e) });
    http.expectOne((r) => r.url.endsWith('/accounting/income-expense/')).flush({}, { status: 400, statusText: 'Bad' });
    expect(error instanceof AccountingApiError).toBeTrue();
  });
});
