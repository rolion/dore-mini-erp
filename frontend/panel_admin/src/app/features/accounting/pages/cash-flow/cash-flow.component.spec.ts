import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { CompactViewportService } from '../../../../core/layout/compact-viewport.service';
import { AccountingApiError } from '../../models/accounting';
import { toCashFlow, toCashFlowMovementPage } from '../../models/cash-flow';
import { CashFlowApiService } from '../../services/cash-flow-api.service';
import { makeCashFlowDto, makeMovementPageDto } from '../../testing/cash-flow-fixtures';
import { CashFlowComponent, cashFlowFiltersFromParams, cashFlowFiltersToQuery } from './cash-flow.component';
import { signal } from '@angular/core';

describe('CashFlowComponent', () => {
  function create(options: { query?: Record<string, string>; compact?: boolean; summaryError?: boolean; movements?: ReturnType<typeof makeMovementPageDto> } = {}) {
    const api = jasmine.createSpyObj<CashFlowApiService>('CashFlowApiService', ['summary', 'movements']);
    api.summary.and.returnValue(options.summaryError ? throwError(() => new AccountingApiError('Falló', 500)) : of(toCashFlow(makeCashFlowDto())));
    api.movements.and.returnValue(of(toCashFlowMovementPage(options.movements ?? makeMovementPageDto())));
    const query = options.query ?? { date_from: '2026-05-01', date_to: '2026-05-31' };
    const params = new BehaviorSubject(convertToParamMap(query));
    TestBed.configureTestingModule({
      imports: [CashFlowComponent],
      providers: [
        ...provideTestTranslations(), provideRouter([]),
        { provide: CashFlowApiService, useValue: api },
        { provide: CompactViewportService, useValue: { compact: signal(options.compact ?? false) } },
        { provide: ActivatedRoute, useValue: { queryParamMap: params, snapshot: { queryParamMap: convertToParamMap(query) } } },
      ],
    });
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    const fixture = TestBed.createComponent(CashFlowComponent);
    fixture.detectChanges();
    return { fixture, api, navigate, el: fixture.nativeElement as HTMLElement };
  }
  const byId = (el: HTMLElement, id: string): HTMLElement | null => el.querySelector(`[data-testid="${id}"]`);

  it('shows the summary and loads both resources for the range in the URL (AC-01, AC-03)', () => {
    const { el, api } = create();
    expect(api.summary).toHaveBeenCalledWith('2026-05-01', '2026-05-31');
    expect(byId(el, 'opening')?.textContent).toContain('0.00');
    expect(byId(el, 'inflow')?.textContent).toContain('2477.00');
    expect(byId(el, 'outflow')?.textContent).toContain('1750.00');
    expect(byId(el, 'net')?.textContent).toContain('727.00');
    expect(byId(el, 'closing')?.textContent).toContain('727.00');
    expect(byId(el, 'transfers-note')?.textContent).toContain('500.00');
  });

  it('shows the per-account breakdown with transfers sent and received (AC-04)', () => {
    const { el } = create();
    const rows = el.querySelectorAll('[data-testid="account-row"]');
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toContain('Caja');
    expect(rows[0].textContent).toContain('500.00');
    expect(rows[1].textContent).toContain('Banco');
    expect(byId(el, 'accounts-total')).not.toBeNull();
  });

  it('selecting an account filters the movements through the URL and can be removed (AC-06)', () => {
    const { el, navigate } = create();
    (el.querySelector('[data-testid="account-select"]') as HTMLButtonElement).click();
    expect(navigate).toHaveBeenCalledWith(['/pocketbiz/accounting/cash-flow'], { queryParams: { date_from: '2026-05-01', date_to: '2026-05-31', account: 'a-cash' } });
  });

  it('applies the account and type from the URL to the movements request and shows the chip (AC-06)', () => {
    const { el, api } = create({ query: { date_from: '2026-05-01', date_to: '2026-05-31', account: 'a-cash', type: 'transfer' } });
    expect(api.movements).toHaveBeenCalledWith({ dateFrom: '2026-05-01', dateTo: '2026-05-31', accountId: 'a-cash', type: 'transfer' }, 1, 20);
    expect(byId(el, 'account-chip')?.textContent).toContain('Caja');
    expect(el.querySelector('[data-testid="account-row"].table-active')).not.toBeNull();
  });

  it('shows each movement with its type, sign, reversal mark, origin link and a link to the entry (AC-05, AC-07)', () => {
    const { el } = create();
    const rows = el.querySelectorAll('[data-testid="movement-row"]');
    expect(rows.length).toBe(2);
    expect(rows[0].querySelector('[data-testid="amount"]')?.textContent).toContain('+ Bs 90.00');
    expect(rows[0].querySelector('[data-testid="kind-badge"]')?.textContent).toContain('Entrada');
    expect(rows[0].querySelector('[data-testid="origin-link"]')?.getAttribute('href')).toBe('/pocketbiz/sales/orders/o-1');
    expect(rows[0].querySelector('[data-testid="view-entry"]')?.getAttribute('href')).toBe('/pocketbiz/accounting/journal/e-1');
    expect(rows[1].querySelector('[data-testid="amount"]')?.textContent).toContain('− Bs 500.00');
    expect(rows[1].querySelector('[data-testid="reversal-badge"]')).not.toBeNull();
    expect(rows[1].querySelector('[data-testid="origin-link"]')).toBeNull();
  });

  it('shows the empty state with active filters and a way to clear them', () => {
    const { el } = create({ query: { date_from: '2026-05-01', date_to: '2026-05-31', type: 'outflow' }, movements: makeMovementPageDto({ count: 0, results: [] }) });
    expect(byId(el, 'empty')).not.toBeNull();
    expect(byId(el, 'applied-filter')).not.toBeNull();
    expect(byId(el, 'empty-clear')).not.toBeNull();
  });

  it('shows an error with retry when the summary fails (and keeps the movements)', () => {
    const { el, api } = create({ summaryError: true });
    expect(byId(el, 'flow-error')?.textContent).toContain('Falló');
    (byId(el, 'retry-flow') as HTMLButtonElement).click();
    expect(api.summary).toHaveBeenCalledTimes(2);
    expect(el.querySelectorAll('[data-testid="movement-row"]').length).toBe(2);
  });

  it('rejects an inverted range without navigating', () => {
    const { fixture, el, navigate } = create();
    fixture.componentInstance.filterForm.patchValue({ dateFrom: '2026-06-01', dateTo: '2026-05-01' });
    fixture.componentInstance.applyForm();
    fixture.detectChanges();
    expect(navigate).not.toHaveBeenCalled();
    expect(byId(el, 'range-error')).not.toBeNull();
  });

  it('uses cards on narrow screens and keeps the entry link', () => {
    const { el } = create({ compact: true });
    expect(el.querySelector('[data-testid="movements-table"]')).toBeNull();
    expect(el.querySelectorAll('[data-testid="movement-card"]').length).toBe(2);
    expect(el.querySelectorAll('[data-testid="account-card"]').length).toBe(2);
    expect(el.querySelector('[data-testid="card-view"]')?.getAttribute('href')).toBe('/pocketbiz/accounting/journal/e-1');
  });

  it('warns when the coverage is partial', () => {
    const api = jasmine.createSpyObj<CashFlowApiService>('CashFlowApiService', ['summary', 'movements']);
    api.summary.and.returnValue(of(toCashFlow(makeCashFlowDto({ coverage: { cutoff_date: '2026-04-01', partial: true } }))));
    api.movements.and.returnValue(of(toCashFlowMovementPage(makeMovementPageDto())));
    TestBed.configureTestingModule({
      imports: [CashFlowComponent],
      providers: [...provideTestTranslations(), provideRouter([]), { provide: CashFlowApiService, useValue: api }],
    });
    const fixture = TestBed.createComponent(CashFlowComponent);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="coverage"]')?.textContent).toContain('01/04/2026');
  });

  it('reads and writes filters from the URL', () => {
    expect(cashFlowFiltersFromParams(convertToParamMap({ date_from: '2026-05-01', date_to: '2026-05-31', account: 'x', type: 'bad' })))
      .toEqual({ dateFrom: '2026-05-01', dateTo: '2026-05-31', accountId: 'x', type: '' });
    expect(cashFlowFiltersToQuery({ dateFrom: 'a', dateTo: 'b', accountId: 'x', type: 'inflow' }, 2)).toEqual({ date_from: 'a', date_to: 'b', account: 'x', type: 'inflow', page: 3 });
  });
});
