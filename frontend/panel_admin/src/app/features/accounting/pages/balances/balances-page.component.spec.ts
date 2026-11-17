import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { FiscalPeriod } from '../../models/fiscal-period';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AccountingApiError } from '../../models/accounting';
import { Balances, toBalances } from '../../models/balances';
import { AccountingApiService } from '../../services/accounting-api.service';
import { BalancesApiService } from '../../services/balances-api.service';
import { FiscalPeriodsApiService } from '../../services/fiscal-periods-api.service';
import { makeBalanceRowDto, makeBalancesDto } from '../../testing/balances-fixtures';
import { BalancesPageComponent, balanceFiltersFromParams, balanceFiltersToQuery } from './balances-page.component';

describe('BalancesPageComponent', () => {
  const PERIOD: FiscalPeriod = { id: 'p-1', name: 'Q4', startDate: '2026-10-01', endDate: '2026-12-31', status: 'OPEN', isOpen: true, closedByName: '' };

  function create(result: Balances | Error, query: Record<string, string> = {}, periodList: FiscalPeriod[] = [PERIOD]) {
    const api = jasmine.createSpyObj<BalancesApiService>('BalancesApiService', ['get']);
    api.get.and.returnValue(result instanceof Error ? throwError(() => result) : of(result));
    const accounting = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listAccounts']);
    accounting.listAccounts.and.returnValue(of([]));
    const periods = jasmine.createSpyObj<FiscalPeriodsApiService>('FiscalPeriodsApiService', ['list']);
    periods.list.and.returnValue(of(periodList));
    const params = new BehaviorSubject(convertToParamMap(query));
    TestBed.configureTestingModule({
      imports: [BalancesPageComponent],
      providers: [
        ...provideTestTranslations(), provideRouter([]),
        { provide: BalancesApiService, useValue: api },
        { provide: AccountingApiService, useValue: accounting },
        { provide: FiscalPeriodsApiService, useValue: periods },
        { provide: ActivatedRoute, useValue: { queryParamMap: params, snapshot: { queryParamMap: convertToParamMap(query) } } },
      ],
    });
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    const fixture = TestBed.createComponent(BalancesPageComponent);
    fixture.detectChanges();
    return { fixture, api, navigate, component: fixture.componentInstance, el: fixture.nativeElement as HTMLElement };
  }

  it('shows every account with debit and credit balances and the totals (AC-01, AC-08)', () => {
    const { el } = create(toBalances(makeBalancesDto()));
    const rows = el.querySelectorAll('[data-testid="balance-row"]');
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toContain('Caja');
    expect(rows[0].querySelector('[data-testid="debit-balance"]')?.textContent).toContain('700.00');
    expect(rows[1].querySelector('[data-testid="credit-balance"]')?.textContent).toContain('700.00');
    expect(el.querySelector('[data-testid="total-debit"]')?.textContent).toContain('1300.00');
    expect(el.querySelector('[data-testid="balanced-badge"]')).not.toBeNull();
    expect(el.querySelectorAll('thead th').length).toBe(7);
  });

  it('links each account to its movements with the same range (AC-07)', () => {
    const { el } = create(toBalances(makeBalancesDto()), { date_from: '2026-11-01', date_to: '2026-11-30' });
    const href = el.querySelector('[data-testid="movements-link"]')?.getAttribute('href') ?? '';
    expect(href).toContain('/accounting/journal');
    expect(href).toContain('account_id=a-1');
    expect(href).toContain('date_from=2026-11-01');
    expect(href).toContain('date_to=2026-11-30');
  });

  it('adds the opening columns only when the range has a start (AC-05)', () => {
    const { el } = create(toBalances(makeBalancesDto({ has_opening: true, date_from: '2026-11-01' })), { date_from: '2026-11-01' });
    expect(el.querySelectorAll('thead th').length).toBe(9);
  });

  it('marks disabled and unclassified accounts and the unbalanced totals (AC-03)', () => {
    const dto = makeBalancesDto({ rows: [makeBalanceRowDto({ is_active: false, account_class: null, code: null })] });
    dto.totals.balanced = false;
    const { el } = create(toBalances(dto));
    expect(el.querySelector('[data-testid="disabled-badge"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="unclassified"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="unbalanced-badge"]')).not.toBeNull();
  });

  it('shows the empty state with the applied filters and a way to clear them', () => {
    const { el } = create(toBalances(makeBalancesDto({ rows: [] })), { account_class: 'COST' });
    expect(el.querySelector('[data-testid="empty"]')).not.toBeNull();
    expect(el.querySelectorAll('[data-testid="applied-filter"]').length).toBe(1);
    expect(el.querySelector('[data-testid="empty-clear"]')).not.toBeNull();
  });

  it('shows the server error with a retry (AC-08)', () => {
    const { el, api } = create(new AccountingApiError('Falló', 500));
    expect(el.querySelector('[data-testid="list-error"]')?.textContent).toContain('Falló');
    (el.querySelector('[data-testid="retry"]') as HTMLButtonElement).click();
    expect(api.get).toHaveBeenCalledTimes(2);
  });

  it('does not query when the range is inverted', () => {
    const { el, api } = create(toBalances(makeBalancesDto()), { date_from: '2026-12-01', date_to: '2026-11-01' });
    expect(api.get).not.toHaveBeenCalled();
    expect(el.querySelector('[data-testid="range-error"]')).not.toBeNull();
  });

  it('reads filters from the URL and ignores unknown classes', () => {
    expect(balanceFiltersFromParams(convertToParamMap({ account_class: 'X' })).accountClass).toBe('');
    expect(balanceFiltersToQuery({ dateFrom: '', dateTo: '', accountClass: '', accountId: '' })).toEqual({});
    expect(balanceFiltersToQuery({ dateFrom: '2026-11-01', dateTo: '', accountClass: 'ASSET', accountId: 'a-1' }))
      .toEqual({ date_from: '2026-11-01', account_class: 'ASSET', account_id: 'a-1' });
  });

  it('fills Desde/Hasta from the chosen fiscal period and puts them in the URL (AC-06)', () => {
    const { component, navigate } = create(toBalances(makeBalancesDto()));
    component.onPeriod('p-1');
    expect(component.filterForm.getRawValue().dateFrom).toBe('2026-10-01');
    expect(component.filterForm.getRawValue().dateTo).toBe('2026-12-31');
    expect(component.periodId).toBe('p-1');
    expect(navigate.calls.mostRecent().args[1]?.queryParams).toEqual({ date_from: '2026-10-01', date_to: '2026-12-31' });
  });

  it('drops the period selection when the dates no longer match it', () => {
    const { component } = create(toBalances(makeBalancesDto()));
    component.onPeriod('p-1');
    component.filterForm.patchValue({ dateFrom: '2026-10-05' });
    expect(component.periodId).toBe('');
    component.onPeriod('');
    expect(component.filterForm.getRawValue().dateFrom).toBe('');
  });

  it('sends every changed filter to the URL and clears them all', () => {
    const { component, navigate } = create(toBalances(makeBalancesDto()));
    component.filterForm.patchValue({ accountClass: 'ASSET', accountId: 'a-1' });
    expect(navigate.calls.mostRecent().args[1]?.queryParams).toEqual({ account_class: 'ASSET', account_id: 'a-1' });
    component.clearFilters();
    expect(component.filterForm.getRawValue()).toEqual({ dateFrom: '', dateTo: '', accountClass: '', accountId: '' });
    expect(navigate.calls.mostRecent().args[1]?.queryParams).toEqual({});
  });

  it('labels classes, unclassified accounts and applied filters', () => {
    const { component } = create(toBalances(makeBalancesDto()), { date_from: '2026-11-01', date_to: '2026-11-30', account_class: 'ASSET', account_id: 'a-9' });
    expect(component.classLabel(null)).toBe('Sin clasificar');
    expect(component.classLabel('ASSET')).toBe('Activo');
    expect(component.appliedFilters.length).toBe(4);
    expect(component.appliedFilters.some((f) => f.includes('a-9'))).toBeTrue();
  });
});
