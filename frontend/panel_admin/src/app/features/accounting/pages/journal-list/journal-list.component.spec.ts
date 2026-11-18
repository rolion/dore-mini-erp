import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { CompactViewportService } from '../../../../core/layout/compact-viewport.service';
import { AccountingApiError } from '../../models/accounting';
import { JournalPage } from '../../models/journal';
import { AccountingApiService } from '../../services/accounting-api.service';
import { JournalApiService } from '../../services/journal-api.service';
import { JournalFiltersState } from '../../services/journal-filters-state';
import { makeJournalRow } from '../../testing/journal-fixtures';
import { JournalListComponent, journalFiltersFromParams, journalFiltersToQuery } from './journal-list.component';

describe('JournalListComponent', () => {
  function create(page: JournalPage | Error, query: Record<string, string> = {}, compact = false) {
    const journal = jasmine.createSpyObj<JournalApiService>('JournalApiService', ['list']);
    journal.list.and.returnValue(page instanceof Error ? throwError(() => page) : of(page));
    const accounting = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listAccounts']);
    accounting.listAccounts.and.returnValue(of([]));
    const params = new BehaviorSubject(convertToParamMap(query));
    TestBed.configureTestingModule({
      imports: [JournalListComponent],
      providers: [
        ...provideTestTranslations(), provideRouter([]),
        { provide: CompactViewportService, useValue: { compact: signal(compact).asReadonly() } },
        { provide: JournalApiService, useValue: journal },
        { provide: AccountingApiService, useValue: accounting },
        { provide: ActivatedRoute, useValue: { queryParamMap: params, snapshot: { queryParamMap: convertToParamMap(query) } } },
      ],
    });
    const fixture = TestBed.createComponent(JournalListComponent);
    fixture.detectChanges();
    return { fixture, journal, el: fixture.nativeElement as HTMLElement };
  }

  it('lists entries and reads filters and page from the URL (AC-03)', () => {
    const { journal, el } = create(
      { count: 1, results: [makeJournalRow({ description: 'Venta mostrador' })] },
      { date_from: '2026-05-01', source: 'MANUAL', account_id: 'a-1', page: '2' },
    );
    expect(journal.list).toHaveBeenCalledWith(jasmine.objectContaining({ dateFrom: '2026-05-01', source: 'MANUAL', accountId: 'a-1', page: 2, pageSize: 20 }));
    expect(el.textContent).toContain('Venta mostrador');
    expect(el.querySelector('[data-testid="new-entry"]')).not.toBeNull();
    expect(el.querySelector('.btn-danger')).toBeNull(); // sin editar ni borrar
  });

  it('ignores an unknown source and an invalid page', () => {
    expect(journalFiltersFromParams(convertToParamMap({ source: 'X' })).source).toBe('');
    expect(journalFiltersToQuery({ dateFrom: '', dateTo: '', accountId: '', source: '' }, 0)).toEqual({});
    expect(journalFiltersToQuery({ dateFrom: '2026-05-01', dateTo: '', accountId: '', source: 'AUTOMATIC' }, 2)).toEqual({ date_from: '2026-05-01', source: 'AUTOMATIC', page: 3 });
  });

  it('shows the empty book with an action to create the first entry', () => {
    const { el } = create({ count: 0, results: [] });
    expect(el.querySelector('[data-testid="empty-book"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="empty-filtered"]')).toBeNull();
  });

  it('shows the filtered empty state with the applied filters and a way to clear them', () => {
    const { el } = create({ count: 0, results: [] }, { source: 'AUTOMATIC' });
    expect(el.querySelector('[data-testid="empty-filtered"]')).not.toBeNull();
    expect(el.querySelectorAll('[data-testid="applied-filter"]').length).toBe(1);
  });

  it('shows a server error with retry', () => {
    const { el, journal } = create(new AccountingApiError('Falló', 500));
    expect(el.querySelector('[data-testid="list-error"]')?.textContent).toContain('Falló');
    (el.querySelector('[data-testid="retry"]') as HTMLButtonElement).click();
    expect(journal.list).toHaveBeenCalledTimes(2);
  });

  it('remembers the filters to restore them when coming back from a detail (AC-03)', () => {
    create({ count: 0, results: [] }, { source: 'MANUAL', page: '3' });
    const state = TestBed.inject(JournalFiltersState);
    expect([state.filters.source, state.pageIndex]).toEqual(['MANUAL', 2]);
  });

  it('puts the filters in the URL when the form changes', () => {
    const { fixture } = create({ count: 0, results: [] });
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    fixture.componentInstance.filterForm.patchValue({ source: 'MANUAL' }, { emitEvent: false });
    fixture.componentInstance.applyForm();
    expect(navigate).toHaveBeenCalledWith(['/pocketbiz/accounting/journal'], { queryParams: { source: 'MANUAL' } });
    fixture.componentInstance.filterForm.patchValue({ dateFrom: '2026-06-01', dateTo: '2026-05-01' }, { emitEvent: false });
    navigate.calls.reset();
    fixture.componentInstance.applyForm();
    expect(fixture.componentInstance.rangeInvalid).toBeTrue();
    expect(navigate).not.toHaveBeenCalled();
  });

  describe('pantalla estrecha', () => {
    const rows = [
      makeJournalRow({ id: 'j-1', description: 'Costo de ventas del pedido P-400B90AD', total: '28.00' }),
      makeJournalRow({ id: 'j-2', description: 'Reversión: Gasto', is_reversal: true }),
      makeJournalRow({ id: 'j-3', description: 'Gasto: alquiler', reversed_by_id: 'j-2' }),
    ];

    it('shows one card per entry with description, view action, date, total and origin', () => {
      const { el } = create({ count: 3, results: rows }, {}, true);
      const cards = el.querySelectorAll('[data-testid="journal-card"]');
      expect(cards.length).toBe(3);
      expect(el.querySelector('ngx-datatable')).toBeNull();
      const first = cards[0];
      expect(first.querySelector('h3')?.textContent).toContain('Costo de ventas del pedido P-400B90AD');
      expect(first.querySelector('[data-testid="card-view"]')?.getAttribute('aria-label')).toContain('Costo de ventas del pedido P-400B90AD');
      expect(first.querySelector('[data-testid="total"]')?.textContent).toContain('28.00');
      expect(first.querySelector('[data-testid="source-badge"]')).not.toBeNull();
      expect(first.querySelectorAll('dt').length).toBe(3);
    });

    it('keeps the reversal and reversed badges on the card', () => {
      const { el } = create({ count: 3, results: rows }, {}, true);
      expect(el.querySelectorAll('[data-testid="reversal-badge"]').length).toBe(1);
      expect(el.querySelectorAll('[data-testid="reversed-badge"]').length).toBe(1);
    });

    it('uses the table on a wide screen', () => {
      const { el } = create({ count: 3, results: rows }, {}, false);
      expect(el.querySelector('[data-testid="journal-card"]')).toBeNull();
      expect(el.querySelector('[data-testid="filters-toggle"]')).toBeNull();
    });

    it('hides the filters until the button is pressed and shows the active count and chips', () => {
      const { fixture, el } = create({ count: 3, results: rows }, { source: 'MANUAL' }, true);
      const form = el.querySelector('[data-testid="filters"]') as HTMLElement;
      const toggle = el.querySelector('[data-testid="filters-toggle"]') as HTMLButtonElement;
      expect(form.classList).toContain('d-none');
      expect(toggle.getAttribute('aria-expanded')).toBe('false');
      expect(el.querySelector('[data-testid="filters-count"]')?.textContent?.trim()).toBe('1');
      expect(el.querySelectorAll('[data-testid="filters-chips"] .badge-outline').length).toBe(1);
      toggle.click();
      fixture.detectChanges();
      expect(form.classList).not.toContain('d-none');
      expect(toggle.getAttribute('aria-expanded')).toBe('true');
    });

    it('does not apply on change, applies with «Aplicar» and collapses the panel', async () => {
      jasmine.clock().install();
      try {
        const { fixture, el } = create({ count: 3, results: rows }, {}, true);
        const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
        (el.querySelector('[data-testid="filters-toggle"]') as HTMLButtonElement).click();
        fixture.componentInstance.filterForm.patchValue({ source: 'MANUAL' });
        jasmine.clock().tick(1000);
        expect(navigate).not.toHaveBeenCalled();
        fixture.detectChanges();
        (el.querySelector('[data-testid="apply-filters"]') as HTMLButtonElement).click();
        fixture.detectChanges();
        expect(navigate).toHaveBeenCalledWith(['/pocketbiz/accounting/journal'], { queryParams: { source: 'MANUAL' } });
        expect(fixture.componentInstance.filtersOpen).toBeFalse();
      } finally {
        jasmine.clock().uninstall();
      }
    });

    it('keeps the panel open when the date range is invalid', () => {
      const { fixture, el } = create({ count: 3, results: rows }, {}, true);
      fixture.componentInstance.filtersOpen = true;
      fixture.componentInstance.filterForm.patchValue({ dateFrom: '2026-06-01', dateTo: '2026-05-01' }, { emitEvent: false });
      fixture.componentInstance.applyAndClose();
      fixture.detectChanges();
      expect(fixture.componentInstance.filtersOpen).toBeTrue();
      expect(el.querySelector('[data-testid="range-error"]')).not.toBeNull();
    });

    it('paginates the cards through the URL and reports the visible range', () => {
      const { fixture, el } = create({ count: 45, results: rows }, { page: '2' }, true);
      expect(el.querySelector('[data-testid="range-summary"]')?.textContent).toContain('21');
      const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
      fixture.componentInstance.onPageNumber(3);
      expect(navigate).toHaveBeenCalledWith(['/pocketbiz/accounting/journal'], { queryParams: { page: 3 } });
    });
  });
});
