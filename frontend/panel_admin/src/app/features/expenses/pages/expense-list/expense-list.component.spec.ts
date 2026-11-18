import { CompactViewportService } from '../../../../core/layout/compact-viewport.service';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { ExpensesApiError } from '../../models/api-error';
import { Expense, ExpenseListParams } from '../../models/expense';
import { CategoriesApiService } from '../../services/categories-api.service';
import { ExpensesApiService } from '../../services/expenses-api.service';
import { categoryPage, expensePage, makeCategory, makeExpense } from '../../testing/expense-fixtures';
import { ExpenseListComponent, INVALID_RANGE_MESSAGE } from './expense-list.component';

interface Hooks {
  confirmVoid(expense: Expense): Promise<boolean>;
  today(): Date;
}

describe('ExpenseListComponent', () => {
  let fixture: ComponentFixture<ExpenseListComponent>;
  let component: ExpenseListComponent;
  let api: jasmine.SpyObj<ExpensesApiService>;
  let categoriesApi: jasmine.SpyObj<CategoriesApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  const compact = signal(false);

  const active = makeExpense({ id: 'a', description: 'Harina de maíz' });
  const voided = makeExpense({
    id: 'v',
    description: 'Gasto por error',
    amount: '999.00',
    status: 'VOIDED',
    voidedAt: '2026-10-06T10:00:00Z',
    category: { id: 'cat-2', name: 'Vieja', active: false },
  });

  beforeEach(async () => {
    compact.set(false);
    api = jasmine.createSpyObj<ExpensesApiService>('ExpensesApiService', ['list', 'void']);
    api.list.and.returnValue(of(expensePage([active], '120.50')));
    categoriesApi = jasmine.createSpyObj<CategoriesApiService>('CategoriesApiService', ['list']);
    categoriesApi.list.and.returnValue(
      of(categoryPage([makeCategory(), makeCategory({ id: 'cat-2', name: 'Vieja', active: false })])),
    );
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);

    await TestBed.configureTestingModule({
      imports: [ExpenseListComponent],
      providers: [...provideTestTranslations(), 
        provideRouter([]),
        { provide: ExpensesApiService, useValue: api },
        { provide: CategoriesApiService, useValue: categoriesApi },
        { provide: ToastrService, useValue: toastr },
        { provide: CompactViewportService, useValue: { compact: compact.asReadonly() } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ExpenseListComponent);
    component = fixture.componentInstance;
    spyOn(component as unknown as Hooks, 'today').and.returnValue(new Date(2026, 9, 15));
  });

  const text = () => (fixture.nativeElement as HTMLElement).textContent ?? '';
  const lastParams = (): ExpenseListParams => api.list.calls.mostRecent().args[0] ?? {};

  function render(): void {
    fixture.detectChanges();
    fixture.detectChanges();
  }

  function click(selector: string): void {
    (fixture.debugElement.query(By.css(selector)).nativeElement as HTMLElement).click();
    fixture.detectChanges();
  }

  it('loads this month, only active expenses, 10 per page (AC-21)', () => {
    render();
    expect(api.list).toHaveBeenCalledOnceWith({
      dateFrom: '2026-10-01',
      dateTo: '2026-10-31',
      categoryId: undefined,
      status: 'active',
      page: 1,
      pageSize: 10,
    });
    expect(component.currentShortcut).toBe('month');
  });

  it('shows the filter total taken from the server and the table columns (AC-21)', () => {
    render();
    const total = fixture.debugElement.query(By.css('[data-testid="total"]')).nativeElement as HTMLElement;
    expect(total.textContent).toContain('Bs 120.50');
    expect(total.textContent).not.toContain('anulados no se suman');
    expect(text()).toContain('Harina de maíz');
    expect(text()).toContain('Materia prima');
    expect(text()).toContain('Efectivo');
    expect(text()).toContain('Molino Sur');
    expect(text()).toContain('05/10/2026');
  });

  it('offers every category, marking the inactive ones, and the three states (AC-21)', () => {
    render();
    const options = (selector: string) =>
      fixture.debugElement.queryAll(By.css(selector + ' option')).map((o) => (o.nativeElement as HTMLElement).textContent?.trim());
    expect(options('#filter-category')).toEqual(['Todas', 'Materia prima', 'Vieja (inactiva)']);
    expect(options('#filter-status')).toEqual(['Vigentes', 'Anulados', 'Todos']);
  });

  it('applies the previous-month and "all" shortcuts (AC-21)', () => {
    render();
    click('[data-shortcut="previous-month"]');
    expect(lastParams()).toEqual(jasmine.objectContaining({ dateFrom: '2026-09-01', dateTo: '2026-09-30', page: 1 }));
    expect(component.currentShortcut).toBe('previous-month');
    click('[data-shortcut="all"]');
    expect(lastParams().dateFrom).toBeUndefined();
    expect(lastParams().dateTo).toBeUndefined();
    expect(component.currentShortcut).toBe('all');
  });

  it('limits the result to a category and goes back to the first page (AC-21)', () => {
    render();
    component.onPage({ offset: 2 });
    component.filterForm.controls.categoryId.setValue('cat-1');
    expect(lastParams()).toEqual(jasmine.objectContaining({ categoryId: 'cat-1', page: 1 }));
    expect(component.pageIndex).toBe(0);
  });

  it('asks for voided expenses and warns they are not added up (AC-21)', () => {
    api.list.and.returnValue(of(expensePage([voided, active], '120.50')));
    render();
    component.filterForm.controls.status.setValue('all');
    fixture.detectChanges();
    expect(lastParams().status).toBe('all');
    expect(text()).toContain('Los gastos anulados no se suman.');
  });

  it('dims voided rows and gives them neither edit nor void actions (UI-02)', () => {
    api.list.and.returnValue(of(expensePage([voided, active], '120.50')));
    render();
    component.filterForm.controls.status.setValue('all');
    render();
    const rows = fixture.debugElement.queryAll(By.css('datatable-body-row'));
    expect(rows.length).toBe(2);
    expect((rows[0].nativeElement as HTMLElement).classList).toContain('expense-voided');
    expect(rows[0].queryAll(By.css('[aria-label="Editar"]')).length).toBe(0);
    expect(rows[0].queryAll(By.css('[aria-label="Anular"]')).length).toBe(0);
    expect(rows[1].queryAll(By.css('[aria-label="Anular"]')).length).toBe(1);
    expect(text()).toContain('(inactiva)');
  });

  it('does not query with an inverted range and says why (AC-21)', () => {
    render();
    api.list.calls.reset();
    component.filterForm.patchValue({ dateFrom: '2026-10-20', dateTo: '2026-10-10' });
    fixture.detectChanges();
    expect(api.list).not.toHaveBeenCalled();
    expect(text()).toContain(INVALID_RANGE_MESSAGE());
  });

  it('clears the filters back to active expenses without dates (AC-21)', () => {
    render();
    component.filterForm.patchValue({ categoryId: 'cat-1', status: 'voided' });
    component.clearFilters();
    expect(component.filterForm.getRawValue()).toEqual({ dateFrom: '', dateTo: '', categoryId: '', status: 'active' });
    expect(component.filtersActive).toBeFalse();
  });

  it('voids after confirming and reloads (AC-23)', async () => {
    api.void.and.returnValue(of(voided));
    spyOn(component as unknown as Hooks, 'confirmVoid').and.resolveTo(true);
    render();
    api.list.calls.reset();
    await component.voidExpense(active);
    expect(api.void).toHaveBeenCalledOnceWith('a');
    expect(toastr.success).toHaveBeenCalledWith('Gasto anulado');
    expect(api.list).toHaveBeenCalledTimes(1);
  });

  it('does nothing when the user cancels the confirmation', async () => {
    spyOn(component as unknown as Hooks, 'confirmVoid').and.resolveTo(false);
    render();
    await component.voidExpense(active);
    expect(api.void).not.toHaveBeenCalled();
  });

  it('reports a failed void without reloading', async () => {
    api.void.and.returnValue(throwError(() => new ExpensesApiError('El gasto ya está anulado.', 409)));
    spyOn(component as unknown as Hooks, 'confirmVoid').and.resolveTo(true);
    render();
    api.list.calls.reset();
    await component.voidExpense(active);
    expect(toastr.error).toHaveBeenCalledWith('El gasto ya está anulado.');
    expect(api.list).not.toHaveBeenCalled();
  });

  it('reports a failed load and stops loading', () => {
    api.list.and.returnValue(throwError(() => new ExpensesApiError('No se pudo conectar con el servidor.', 0)));
    render();
    expect(toastr.error).toHaveBeenCalledWith('No se pudo conectar con el servidor.');
    expect(component.loading).toBeFalse();
  });

  describe('desktop (>= 992 px) (AC-01)', () => {
    it('keeps the table, the period buttons and always-visible filters', () => {
      render();
      const q = (selector: string) => fixture.debugElement.query(By.css(selector));
      expect(q('ngx-datatable')).not.toBeNull();
      expect(q('[data-testid="shortcuts"]')).not.toBeNull();
      expect(q('[data-testid="filters"]')?.nativeElement.classList).not.toContain('d-none');
      expect(q('[data-testid="filters-toggle"]')).toBeNull();
      expect(q('[data-testid="period-select"]')).toBeNull();
      expect(q('[data-testid="expense-card"]')).toBeNull();
    });
  });

  describe('compact (< 992 px)', () => {
    const q = (selector: string): HTMLElement | null =>
      (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>(selector);
    const qa = (selector: string): HTMLElement[] =>
      Array.from((fixture.nativeElement as HTMLElement).querySelectorAll<HTMLElement>(selector));

    function type(selector: string, value: string): void {
      const el = q(selector) as HTMLInputElement | HTMLSelectElement;
      el.value = value;
      el.dispatchEvent(new Event(el instanceof HTMLSelectElement ? 'change' : 'input'));
      fixture.detectChanges();
    }

    beforeEach(() => compact.set(true));

    it('puts the register button before the filters, with a closed panel and cards instead of the table (AC-02, AC-06)', () => {
      render();
      const html = (fixture.nativeElement as HTMLElement).innerHTML;
      expect(html.indexOf('data-testid="new-expense"')).toBeGreaterThan(-1);
      expect(html.indexOf('data-testid="new-expense"')).toBeLessThan(html.indexOf('data-testid="filters-toggle"'));
      expect(q('ngx-datatable')).toBeNull();
      expect(q('[data-testid="shortcuts"]')).toBeNull();
      expect(q('#expense-filters')?.classList).toContain('d-none');
      const toggle = q('[data-testid="filters-toggle"]');
      expect(toggle?.getAttribute('aria-expanded')).toBe('false');
      expect(toggle?.getAttribute('aria-controls')).toBe('expense-filters');
      expect(q('[data-testid="filters-chips"]')?.textContent).toContain('Este mes');
      expect(q('[data-testid="filters-count"]')?.textContent).toContain('1');
    });

    it('opens the panel with the period first, then dates, category and status (AC-03)', () => {
      render();
      click('[data-testid="filters-toggle"]');
      expect(q('#expense-filters')?.classList).not.toContain('d-none');
      expect(q('[data-testid="filters-toggle"]')?.getAttribute('aria-expanded')).toBe('true');
      const ids = qa('#expense-filters select, #expense-filters input').map((el) => el.id);
      expect(ids).toEqual(['filter-period', 'filter-from', 'filter-to', 'filter-category', 'filter-status']);
      const options = qa('#filter-period option').map((o) => o.textContent?.trim());
      expect(options).toEqual(['Personalizado', 'Este mes', 'Mes anterior', 'Todo']);
    });

    it('preloads the dates from the period select without querying, and goes neutral on a manual edit (AC-03)', () => {
      render();
      click('[data-testid="filters-toggle"]');
      api.list.calls.reset();
      type('#filter-period', 'previous-month');
      expect((q('#filter-from') as HTMLInputElement).value).toBe('2026-09-01');
      expect((q('#filter-to') as HTMLInputElement).value).toBe('2026-09-30');
      expect(api.list).not.toHaveBeenCalled();
      type('#filter-from', '2026-09-05');
      expect((q('#filter-period') as HTMLSelectElement).value).toBe('');
      expect(component.currentShortcut).toBeNull();
      type('#filter-from', '2026-09-01');
      expect((q('#filter-period') as HTMLSelectElement).value).toBe('previous-month');
    });

    it('applies the panel values, folds the panel and focuses the summary (AC-04, AC-05)', async () => {
      render();
      click('[data-testid="filters-toggle"]');
      type('#filter-category', 'cat-1');
      expect(api.list).toHaveBeenCalledTimes(1);
      click('[data-testid="apply-filters"]');
      await Promise.resolve();
      expect(api.list).toHaveBeenCalledTimes(2);
      expect(lastParams()).toEqual(jasmine.objectContaining({ categoryId: 'cat-1', page: 1 }));
      expect(q('#expense-filters')?.classList).toContain('d-none');
      expect(document.activeElement).toBe(q('[data-testid="range-summary"]'));
      expect(q('[data-testid="range-summary"]')?.textContent).toContain('Mostrando 1–1 de 1');
      expect(q('[data-testid="filters-count"]')?.textContent).toContain('2');
      expect(q('[data-testid="total"]')?.textContent).toContain('Bs 120.50');
    });

    it('keeps the panel open and does not query with an inverted range (AC-04)', () => {
      render();
      click('[data-testid="filters-toggle"]');
      api.list.calls.reset();
      type('#filter-from', '2026-10-20');
      type('#filter-to', '2026-10-10');
      click('[data-testid="apply-filters"]');
      expect(api.list).not.toHaveBeenCalled();
      expect(q('#expense-filters')?.classList).not.toContain('d-none');
      expect(q('[data-testid="range-error"]')?.textContent).toContain(INVALID_RANGE_MESSAGE());
    });

    it('clears the filters, folds the panel and queries (AC-04)', () => {
      render();
      click('[data-testid="filters-toggle"]');
      api.list.calls.reset();
      click('[data-testid="clear-filters"]');
      expect(lastParams().dateFrom).toBeUndefined();
      expect(lastParams().status).toBe('active');
      expect(q('#expense-filters')?.classList).toContain('d-none');
    });

    it('shows one card per expense with its data and actions by state (AC-06)', () => {
      api.list.and.returnValue(of(expensePage([voided, makeExpense({ supplierName: '' }), active], '120.50')));
      render();
      component.filterForm.controls.status.setValue('all');
      component.applyAndClose();
      render();
      const cards = qa('[data-testid="expense-card"]');
      expect(cards.length).toBe(3);
      const [voidedCard, noSupplier, activeCard] = cards;
      expect(voidedCard.querySelector('[data-testid="card-edit"]')).toBeNull();
      expect(voidedCard.querySelector('[data-testid="card-void"]')).toBeNull();
      expect(voidedCard.querySelector('[data-testid="card-status"]')?.textContent).toContain('Anulado');
      expect(voidedCard.classList).toContain('expense-card--voided');
      expect(voidedCard.textContent).toContain('(inactiva)');
      expect(noSupplier.querySelector('[data-testid="card-no-supplier"]')?.textContent).toContain('—');
      expect(activeCard.querySelector('[data-testid="card-description"]')?.textContent).toContain('Harina de maíz');
      expect(activeCard.querySelector('[data-testid="card-date"]')?.textContent).toContain('05/10/2026');
      expect(activeCard.querySelector('[data-testid="card-amount"]')?.textContent).toContain('Bs');
      expect(activeCard.querySelector('[data-testid="card-status"]')?.textContent).toContain('Vigente');
      expect(activeCard.textContent).toContain('Efectivo');
      expect(activeCard.textContent).toContain('Molino Sur');
      expect(activeCard.querySelector('[data-testid="card-view"]')).not.toBeNull();
      expect(activeCard.querySelector('[data-testid="card-edit"]')).not.toBeNull();
    });

    it('voids from a card after confirming (AC-06)', async () => {
      api.void.and.returnValue(of(voided));
      spyOn(component as unknown as Hooks, 'confirmVoid').and.resolveTo(true);
      render();
      click('[data-testid="card-void"]');
      await fixture.whenStable();
      expect(api.void).toHaveBeenCalledOnceWith('a');
    });

    it('paginates the cards and asks for the chosen page keeping the applied filters (AC-06)', () => {
      api.list.and.returnValue(of({ ...expensePage([active], '120.50'), count: 25 }));
      render();
      expect(q('ngb-pagination')).not.toBeNull();
      component.onCardsPage(3);
      expect(lastParams()).toEqual(jasmine.objectContaining({ page: 3, dateFrom: '2026-10-01' }));
    });

    it('explains an empty result with each applied filter, clear and register actions (AC-07)', () => {
      api.list.and.returnValue(of(expensePage([], '0.00')));
      render();
      expect(q('[data-testid="empty-filtered"]')).not.toBeNull();
      expect(qa('[data-testid="applied-filter"]').map((el) => el.textContent?.trim())).toEqual(['Este mes']);
      expect(q('[data-testid="empty-clear"]')).not.toBeNull();
      expect(q('[data-testid="empty-new"]')?.getAttribute('href')).toBe('/pocketbiz/expenses/new');
    });

    it('shows only the plain message when nothing is filtered (AC-07)', () => {
      api.list.and.returnValue(of(expensePage([], '0.00')));
      render();
      component.period.setValue('all');
      component.applyAndClose();
      render();
      expect(q('[data-testid="empty-filtered"]')).toBeNull();
      expect(q('[data-testid="cards-empty"]')?.textContent).toContain('No hay gastos que coincidan');
    });
  });
});
