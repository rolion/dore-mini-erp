import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AccountingApiError } from '../../models/accounting';
import { BalanceSheet, toBalanceSheet } from '../../models/balance-sheet';
import { BalanceSheetApiService } from '../../services/balance-sheet-api.service';
import { makeBalanceSheetDto } from '../../testing/balance-sheet-fixtures';
import { BalanceSheetComponent, balanceSheetFiltersFromParams, balanceSheetFiltersToQuery } from './balance-sheet.component';

describe('BalanceSheetComponent', () => {
  function create(result: BalanceSheet | Error, query: Record<string, string> = {}) {
    const api = jasmine.createSpyObj<BalanceSheetApiService>('BalanceSheetApiService', ['get']);
    api.get.and.returnValue(result instanceof Error ? throwError(() => result) : of(result));
    const params = new BehaviorSubject(convertToParamMap(query));
    TestBed.configureTestingModule({
      imports: [BalanceSheetComponent],
      providers: [
        ...provideTestTranslations(), provideRouter([]),
        { provide: BalanceSheetApiService, useValue: api },
        { provide: ActivatedRoute, useValue: { queryParamMap: params, snapshot: { queryParamMap: convertToParamMap(query) } } },
      ],
    });
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    const fixture = TestBed.createComponent(BalanceSheetComponent);
    fixture.detectChanges();
    return { fixture, api, navigate, component: fixture.componentInstance, el: fixture.nativeElement as HTMLElement };
  }

  it('shows the three sections with totals, equity results and the balanced badge (AC-08)', () => {
    const { el } = create(toBalanceSheet(makeBalanceSheetDto()));
    for (const key of ['ASSET', 'LIABILITY', 'EQUITY']) {
      expect(el.querySelector(`[data-testid="section-${key}"]`)).not.toBeNull();
    }
    expect(el.querySelectorAll('[data-testid="sheet-row"]').length).toBe(3);
    expect(el.querySelector('[data-testid="previous-result"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="period-result"]')?.textContent).toContain('200.00');
    expect(el.querySelector('[data-testid="total-assets"]')?.textContent).toContain('1500.00');
    expect(el.querySelector('[data-testid="total-liabilities-equity"]')?.textContent).toContain('1500.00');
    expect(el.querySelector('[data-testid="balanced-badge"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="unclassified-warning"]')).toBeNull();
  });

  it('shows opening and movement columns only with a start date (AC-09)', () => {
    const without = create(toBalanceSheet(makeBalanceSheetDto()));
    expect(without.el.querySelectorAll('[data-testid="section-ASSET"] thead th').length).toBe(3);
    TestBed.resetTestingModule();
    const withFrom = create(toBalanceSheet(makeBalanceSheetDto({ date_from: '2026-02-01', has_opening: true })), { date_from: '2026-02-01' });
    expect(withFrom.el.querySelectorAll('[data-testid="section-ASSET"] thead th').length).toBe(5);
  });

  it('warns about unclassified balance and the difference when it does not balance (AC-08)', () => {
    const dto = makeBalanceSheetDto();
    dto.totals = { ...dto.totals, balanced: false, difference: '50.00', unclassified_balance: '-50.00' };
    const { el } = create(toBalanceSheet(dto));
    expect(el.querySelector('[data-testid="unclassified-warning"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="unbalanced-badge"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="difference"]')).not.toBeNull();
  });

  it('marks negative amounts with text-danger and the minus sign', () => {
    const dto = makeBalanceSheetDto();
    dto.sections[0].rows[0] = { ...dto.sections[0].rows[0], closing: '-200.00' };
    const { el } = create(toBalanceSheet(dto));
    const cell = el.querySelector('[data-testid="row-closing"]');
    expect(cell?.classList).toContain('text-danger');
    expect(cell?.textContent).toContain('-200.00');
  });

  it('reads filters from the URL and calls the API with them (AC-02)', () => {
    const { api } = create(toBalanceSheet(makeBalanceSheetDto()), { date_from: '2026-01-01', date_to: '2026-03-31' });
    expect(api.get).toHaveBeenCalledWith({ dateFrom: '2026-01-01', dateTo: '2026-03-31' });
  });

  it('writes filters to the URL when the form changes', () => {
    const { component, navigate } = create(toBalanceSheet(makeBalanceSheetDto()));
    component.filterForm.patchValue({ dateTo: '2026-06-30' });
    expect(navigate).toHaveBeenCalled();
    expect(navigate.calls.mostRecent().args[1]?.queryParams).toEqual({ date_to: '2026-06-30' });
  });

  it('shows the range error and does not call the API for an inverted range (AC-06)', () => {
    const { el, api } = create(toBalanceSheet(makeBalanceSheetDto()), { date_from: '2026-05-02', date_to: '2026-05-01' });
    expect(el.querySelector('[data-testid="range-error"]')).not.toBeNull();
    expect(api.get).not.toHaveBeenCalled();
  });

  it('shows the error with retry', () => {
    const { el, api } = create(new AccountingApiError('Falló', 500, {}));
    expect(el.querySelector('[data-testid="list-error"]')?.textContent).toContain('Falló');
    (el.querySelector('[data-testid="retry"]') as HTMLButtonElement).click();
    expect(api.get).toHaveBeenCalledTimes(2);
  });

  it('shows the empty state with a clear button when filters are active', () => {
    const zero = { opening: '0.00', movement: '0.00', closing: '0.00' };
    const dto = makeBalanceSheetDto({
      sections: [{ key: 'ASSET', rows: [], total: zero }, { key: 'LIABILITY', rows: [], total: zero },
        { key: 'EQUITY', rows: [], total: zero, previous_result: zero, period_result: zero }],
      totals: { assets: '0.00', liabilities: '0.00', equity: '0.00', liabilities_and_equity: '0.00', difference: '0.00',
        balanced: true, unclassified_balance: '0.00' },
    });
    const { el } = create(toBalanceSheet(dto), { date_to: '2026-01-01' });
    expect(el.querySelector('[data-testid="empty"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="empty-clear"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="section-ASSET"]')).toBeNull();
  });

  it('converts filters to and from query params', () => {
    expect(balanceSheetFiltersFromParams(convertToParamMap({ date_from: '2026-01-01' }))).toEqual({ dateFrom: '2026-01-01', dateTo: '' });
    expect(balanceSheetFiltersToQuery({ dateFrom: '', dateTo: '2026-02-02' })).toEqual({ date_to: '2026-02-02' });
  });
});
