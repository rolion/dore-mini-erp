import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AccountingApiError } from '../../models/accounting';
import { FiscalPeriod } from '../../models/fiscal-period';
import { IncomeExpenseReport, toIncomeExpenseReport } from '../../models/income-expense';
import { FiscalPeriodsApiService } from '../../services/fiscal-periods-api.service';
import { IncomeExpenseApiService } from '../../services/income-expense-api.service';
import { makeIncomeExpenseDto } from '../../testing/income-expense-fixtures';
import { IncomeExpenseComponent, incomeExpenseFiltersFromParams, incomeExpenseFiltersToQuery } from './income-expense.component';

describe('IncomeExpenseComponent', () => {
  const PERIOD: FiscalPeriod = { id: 'p-1', name: '2026', startDate: '2026-01-01', endDate: '2026-03-31', status: 'OPEN', isOpen: true, closedByName: '' };
  const OLD: FiscalPeriod = { id: 'p-0', name: '2025', startDate: '2025-01-01', endDate: '2025-12-31', status: 'CLOSED', isOpen: false, closedByName: '' };

  function create(result: IncomeExpenseReport | Error, query: Record<string, string> = {}) {
    const api = jasmine.createSpyObj<IncomeExpenseApiService>('IncomeExpenseApiService', ['get']);
    api.get.and.returnValue(result instanceof Error ? throwError(() => result) : of(result));
    const periods = jasmine.createSpyObj<FiscalPeriodsApiService>('FiscalPeriodsApiService', ['list']);
    periods.list.and.returnValue(of([PERIOD, OLD]));
    const params = new BehaviorSubject(convertToParamMap(query));
    TestBed.configureTestingModule({
      imports: [IncomeExpenseComponent],
      providers: [
        ...provideTestTranslations(), provideRouter([]),
        { provide: IncomeExpenseApiService, useValue: api },
        { provide: FiscalPeriodsApiService, useValue: periods },
        { provide: ActivatedRoute, useValue: { queryParamMap: params, snapshot: { queryParamMap: convertToParamMap(query) } } },
      ],
    });
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    const fixture = TestBed.createComponent(IncomeExpenseComponent);
    fixture.detectChanges();
    return { fixture, api, navigate, component: fixture.componentInstance, el: fixture.nativeElement as HTMLElement };
  }

  const report = () => toIncomeExpenseReport(makeIncomeExpenseDto());
  const monthsShown = (el: HTMLElement) => Array.from(el.querySelectorAll('[data-testid="month"]')).map((c) => c.textContent?.trim());

  it('shows one row per month with the footer totals (AC-01, AC-03)', () => {
    const { el } = create(report());
    expect(el.querySelectorAll('[data-testid="month-row"]').length).toBe(3);
    expect(el.querySelector('[data-testid="total-income"]')?.textContent).toContain('1200.00');
    expect(el.querySelector('[data-testid="total-expense"]')?.textContent).toContain('850.00');
    expect(el.querySelector('[data-testid="total-profit"]')?.textContent).toContain('350.00');
    expect(el.querySelectorAll('thead th').length).toBe(4);
  });

  it('asks for the server default period and shows it selected (AC-04)', () => {
    const { api, el } = create(report());
    expect(api.get).toHaveBeenCalledWith({ periodId: '', months: [] });
    expect((el.querySelector('[data-testid="filter-period"]') as HTMLSelectElement).value).toBe('p-1');
  });

  it('marks a negative profit with text as well as color (UI-03)', () => {
    const { el } = create(report());
    const profit = el.querySelectorAll('[data-testid="profit"]')[1];
    expect(profit.classList).toContain('text-danger');
    expect(profit.textContent).toContain('(');
  });

  it('sorts each column from highest to lowest first and flips on the second click, keeping the footer (AC-06)', () => {
    const { fixture, el } = create(report());
    (el.querySelector('[data-testid="sort-profit"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(monthsShown(el)[0]).toContain('Enero');
    expect(el.querySelector('thead th:nth-child(4)')?.getAttribute('aria-sort')).toBe('descending');
    (el.querySelector('[data-testid="sort-profit"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(monthsShown(el)[0]).toContain('Febrero');
    expect(el.querySelector('thead th:nth-child(4)')?.getAttribute('aria-sort')).toBe('ascending');
    expect(el.querySelector('[data-testid="total-profit"]')?.textContent).toContain('350.00');
  });

  it('offers every month of the period and navigates with the chosen ones (AC-05)', () => {
    const { component, navigate } = create(report());
    expect(component.monthOptions.map((o) => o.id)).toEqual(['2026-01', '2026-02', '2026-03']);
    component.onMonths(['2026-01', '2026-03']);
    expect(navigate).toHaveBeenCalledWith([], jasmine.objectContaining({ queryParams: { period: 'p-1', months: '2026-01,2026-03' } }));
  });

  it('keeps the same month options between change detections so mouse clicks reach ng-select (REV-05)', () => {
    const { fixture, component } = create(report());
    const first = component.monthOptions;
    fixture.detectChanges();
    fixture.detectChanges();
    expect(component.monthOptions).toBe(first);
  });

  it('changing the period resets the months (AC-05)', () => {
    const { component, navigate } = create(report(), { period: 'p-1', months: '2026-01' });
    component.onPeriod('p-0');
    expect(navigate).toHaveBeenCalledWith([], jasmine.objectContaining({ queryParams: { period: 'p-0' } }));
  });

  it('reads and writes the filters from the URL', () => {
    const params = convertToParamMap({ period: 'p-1', months: '2026-01,xx,2026-02' });
    expect(incomeExpenseFiltersFromParams(params)).toEqual({ periodId: 'p-1', months: ['2026-01', '2026-02'] });
    expect(incomeExpenseFiltersToQuery({ periodId: '', months: [] })).toEqual({});
  });

  it('shows the empty state when the company has no fiscal periods (UI-02)', () => {
    const { el } = create(toIncomeExpenseReport(makeIncomeExpenseDto({
      period: null, months: [], totals: { income: '0.00', expense: '0.00', profit: '0.00' } })));
    expect(el.querySelector('[data-testid="empty"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="income-expense-table"]')).toBeNull();
  });

  it('shows the server error with a retry (UI-02)', () => {
    const { api, fixture, el } = create(new AccountingApiError('Falló', 500));
    expect(el.querySelector('[data-testid="list-error"]')?.textContent).toContain('Falló');
    (el.querySelector('[data-testid="retry"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(api.get).toHaveBeenCalledTimes(2);
  });
});
