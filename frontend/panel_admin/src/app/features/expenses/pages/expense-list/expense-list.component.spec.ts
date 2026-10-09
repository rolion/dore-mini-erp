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
    api = jasmine.createSpyObj<ExpensesApiService>('ExpensesApiService', ['list', 'void']);
    api.list.and.returnValue(of(expensePage([active], '120.50')));
    categoriesApi = jasmine.createSpyObj<CategoriesApiService>('CategoriesApiService', ['list']);
    categoriesApi.list.and.returnValue(
      of(categoryPage([makeCategory(), makeCategory({ id: 'cat-2', name: 'Vieja', active: false })])),
    );
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);

    await TestBed.configureTestingModule({
      imports: [ExpenseListComponent],
      providers: [
        provideRouter([]),
        { provide: ExpensesApiService, useValue: api },
        { provide: CategoriesApiService, useValue: categoriesApi },
        { provide: ToastrService, useValue: toastr },
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
    expect(text()).toContain(INVALID_RANGE_MESSAGE);
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
});
