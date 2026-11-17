import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { ExpensesApiError } from '../../models/api-error';
import { PostingOptions } from '../../models/expense';
import { CategoriesApiService } from '../../services/categories-api.service';
import { ExpensesApiService } from '../../services/expenses-api.service';
import { categoryPage, makeCategory, makeExpense } from '../../testing/expense-fixtures';
import { ExpenseFormComponent, NO_CATEGORIES_MESSAGE } from './expense-form.component';

const ACCOUNT_ALQUILER = { id: 'a-rent', code: '510001', name: 'Alquiler', active: true };
const ACCOUNT_LUZ = { id: 'a-luz', code: '510002', name: 'Luz', active: true };
const ACCOUNT_BANCO = { id: 'a-bank', code: '110102', name: 'Banco', active: true };

function options(overrides: Partial<PostingOptions> = {}): PostingOptions {
  return {
    covered: true,
    reason: null,
    expenseAccount: ACCOUNT_ALQUILER,
    paymentAccount: ACCOUNT_BANCO,
    issues: [],
    expenseAccounts: [ACCOUNT_ALQUILER, ACCOUNT_LUZ],
    paymentAccounts: [ACCOUNT_BANCO],
    ...overrides,
  };
}

const NO_COVERAGE = options({ covered: false, expenseAccount: null, paymentAccount: null, expenseAccounts: [], paymentAccounts: [] });

describe('ExpenseFormComponent', () => {
  let fixture: ComponentFixture<ExpenseFormComponent>;
  let component: ExpenseFormComponent;
  let api: jasmine.SpyObj<ExpensesApiService>;
  let categoriesApi: jasmine.SpyObj<CategoriesApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let router: Router;

  async function setup(id: string | null = null): Promise<void> {
    api = jasmine.createSpyObj<ExpensesApiService>('ExpensesApiService', ['get', 'create', 'update', 'postingOptions']);
    api.postingOptions.and.returnValue(of(NO_COVERAGE));
    categoriesApi = jasmine.createSpyObj<CategoriesApiService>('CategoriesApiService', ['list']);
    categoriesApi.list.and.returnValue(of(categoryPage([makeCategory(), makeCategory({ id: 'cat-2', name: 'Empaque' })])));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error', 'warning']);
    await TestBed.configureTestingModule({
      imports: [ExpenseFormComponent],
      providers: [...provideTestTranslations(), 
        provideRouter([]),
        { provide: ExpensesApiService, useValue: api },
        { provide: CategoriesApiService, useValue: categoriesApi },
        { provide: ToastrService, useValue: toastr },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap(id ? { id } : {}) } } },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(ExpenseFormComponent);
    component = fixture.componentInstance;
  }

  const text = () => (fixture.nativeElement as HTMLElement).textContent ?? '';

  function fillValid(): void {
    component.form.patchValue({
      description: '  Cajas  ',
      amount: ' 45.50 ',
      expenseDate: '2026-10-07',
      categoryId: 'cat-2',
      paymentMethod: 'QR',
      supplierName: ' Cartonera ',
      notes: '',
    });
  }

  describe('creating', () => {
    beforeEach(async () => {
      await setup();
      fixture.detectChanges();
    });

    it('starts with today and cash as defaults and only offers active categories (AC-22)', () => {
      expect(categoriesApi.list).toHaveBeenCalledOnceWith({ active: true, pageSize: 100 });
      const today = new Date();
      const expected = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
      expect(component.form.controls.expenseDate.value).toBe(expected);
      expect(component.form.controls.paymentMethod.value).toBe('CASH');
      expect(component.categoryOptions.map((o) => o.label)).toEqual(['Materia prima', 'Empaque']);
      const methods = fixture.debugElement
        .queryAll(By.css('#expense-payment option'))
        .map((o) => (o.nativeElement as HTMLElement).textContent?.trim());
      expect(methods).toEqual(['Efectivo', 'QR', 'Transferencia', 'Tarjeta', 'Otro']);
    });

    it('hides the accounting block without coverage and registers without accounts (GAS-01, AC-06)', () => {
      expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="accounting-block"]')).toBeNull();
      api.create.and.returnValue(of(makeExpense({ id: 'new-1' })));
      fillValid();
      component.onSubmit();
      const sent = api.create.calls.mostRecent().args[0];
      expect(sent.expenseAccountId).toBeUndefined();
      expect(sent.paymentAccountId).toBeUndefined();
      expect(sent.idempotencyKey).toMatch(/^[0-9a-f-]{36}$/);
    });

    it('shows the accounts with defaults and a Debit/Credit preview when covered (GAS-01, UI-01)', () => {
      api.postingOptions.and.returnValue(of(options()));
      fillValid();
      fixture.detectChanges();
      expect(api.postingOptions).toHaveBeenCalledWith('2026-10-07', 'cat-2', 'QR');
      const el = fixture.nativeElement as HTMLElement;
      expect(el.querySelector('[data-testid="accounting-block"]')).not.toBeNull();
      const preview = el.querySelector('[data-testid="posting-preview"]')?.textContent ?? '';
      expect(preview).toContain('Alquiler');
      expect(preview).toContain('Banco');
      expect(component.form.controls.expenseAccountId.value).toBeNull();
    });

    it('sends the chosen accounts and keeps the same key when retrying (GAS-01, AC-04)', () => {
      api.postingOptions.and.returnValue(of(options()));
      api.create.and.returnValue(throwError(() => new ExpensesApiError('x', 409, {}, 'fiscal_period_closed')));
      fillValid();
      fixture.detectChanges();
      component.form.patchValue({ expenseAccountId: 'a-luz', paymentAccountId: 'a-bank' });
      component.onSubmit();
      component.onSubmit();
      const [first, second] = api.create.calls.allArgs().map((args) => args[0]);
      expect(first.expenseAccountId).toBe('a-luz');
      expect(first.paymentAccountId).toBe('a-bank');
      expect(second.idempotencyKey).toBe(first.idempotencyKey);
    });

    it('blocks saving and explains what is missing when covered without accounts (GAS-01, AC-07)', () => {
      api.postingOptions.and.returnValue(
        of(
          options({
            expenseAccount: null,
            issues: [{ code: 'category_required', role: 'EXPENSE_BY_CATEGORY', subject: 'Cuenta de gasto', module: 'expenses', message: 'Indique la categoría', params: {}, problem: null }],
          }),
        ),
      );
      fillValid();
      fixture.detectChanges();
      expect(component.missingAccounts).toBeTrue();
      expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="posting-issues"]')).not.toBeNull();
      expect((fixture.nativeElement as HTMLElement).querySelector('button[type="submit"]')?.hasAttribute('disabled')).toBeTrue();
      component.form.patchValue({ expenseAccountId: 'a-luz' });
      expect(component.missingAccounts).toBeFalse();
    });

    it('shows the accounting error returned by the server without a generic toast (GAS-01, AC-03)', () => {
      api.create.and.returnValue(throwError(() => new ExpensesApiError('El período «Año» está cerrado.', 409, {}, 'fiscal_period_closed')));
      fillValid();
      component.onSubmit();
      fixture.detectChanges();
      expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="posting-error"]')?.textContent).toContain('cerrado');
      expect(toastr.error).not.toHaveBeenCalled();
    });

    it('blocks saving without the required data (AC-22)', () => {
      expect(component.form.invalid).toBeTrue();
      component.onSubmit();
      expect(api.create).not.toHaveBeenCalled();
      fixture.detectChanges();
      expect(text()).toContain('La descripción es obligatoria.');
      expect(text()).toContain('El monto es obligatorio.');
      expect(text()).toContain('La categoría es obligatoria.');
    });

    it('rejects zero, negative and over-precise amounts on the client (AC-22)', () => {
      const amount = component.form.controls.amount;
      for (const bad of ['0', '0.00', '-5', '1.234', 'abc']) {
        amount.setValue(bad);
        expect(amount.invalid).withContext(bad).toBeTrue();
      }
      for (const good of ['0.01', '10', '120.5', '99999.99']) {
        amount.setValue(good);
        expect(amount.valid).withContext(good).toBeTrue();
      }
    });

    it('creates the expense with trimmed values and opens its detail (AC-22)', () => {
      api.create.and.returnValue(of(makeExpense({ id: 'new-1' })));
      fillValid();
      component.onSubmit();
      expect(api.create).toHaveBeenCalledOnceWith({
        description: 'Cajas',
        amount: '45.50',
        categoryId: 'cat-2',
        expenseDate: '2026-10-07',
        paymentMethod: 'QR',
        supplierName: 'Cartonera',
        notes: '',
        idempotencyKey: jasmine.stringMatching(/^[0-9a-f-]{36}$/),
      });
      expect(toastr.success).toHaveBeenCalledWith('Gasto registrado');
      expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/expenses', 'new-1']);
    });

    it('shows the server errors under their field and clears them on edit (AC-22)', () => {
      api.create.and.returnValue(
        throwError(() => new ExpensesApiError('Revisa los datos ingresados.', 400, { amount: ['El monto debe ser mayor a cero.'] })),
      );
      fillValid();
      component.onSubmit();
      fixture.detectChanges();
      expect(text()).toContain('El monto debe ser mayor a cero.');
      expect(toastr.error).not.toHaveBeenCalled();
      expect(component.saving).toBeFalse();
      component.form.controls.amount.setValue('50');
      expect(component.serverErrors).toEqual({});
    });

    it('shows a toast when the failure has no field errors', () => {
      api.create.and.returnValue(throwError(() => new ExpensesApiError('No se pudo conectar con el servidor.', 0)));
      fillValid();
      component.onSubmit();
      expect(toastr.error).toHaveBeenCalledWith('No se pudo conectar con el servidor.');
    });
  });

  it('blocks saving and points to Categories when there are no active categories (AC-22)', async () => {
    await setup();
    categoriesApi.list.and.returnValue(of(categoryPage([])));
    fixture.detectChanges();
    expect(component.noCategories).toBeTrue();
    expect(text()).toContain(NO_CATEGORIES_MESSAGE());
    expect((fixture.debugElement.query(By.css('button[type="submit"]')).nativeElement as HTMLButtonElement).disabled).toBeTrue();
    expect(fixture.debugElement.query(By.css('a[href="/pocketbiz/expenses/categories"]'))).not.toBeNull();
  });

  describe('editing', () => {
    it('loads the expense and updates it (AC-22)', async () => {
      await setup('exp-1');
      api.get.and.returnValue(of(makeExpense({ id: 'exp-1', paymentMethod: 'CARD' })));
      api.update.and.returnValue(of(makeExpense({ id: 'exp-1' })));
      fixture.detectChanges();
      expect(api.get).toHaveBeenCalledWith('exp-1');
      expect(component.form.getRawValue()).toEqual(
        jasmine.objectContaining({ description: 'Harina de maíz', amount: '120.50', categoryId: 'cat-1', paymentMethod: 'CARD' }),
      );
      component.form.controls.amount.setValue('130.00');
      component.onSubmit();
      expect(api.update).toHaveBeenCalledWith('exp-1', jasmine.objectContaining({ amount: '130.00', categoryId: 'cat-1' }));
      expect(toastr.success).toHaveBeenCalledWith('Gasto actualizado');
      expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/expenses', 'exp-1']);
    });

    it('locks the financial fields of a posted expense and still lets the descriptive ones change (GAS-01, AC-08)', async () => {
      await setup('exp-1');
      api.get.and.returnValue(of(makeExpense({ id: 'exp-1', posted: true, expenseAccount: ACCOUNT_ALQUILER, paymentAccount: ACCOUNT_BANCO })));
      api.update.and.returnValue(of(makeExpense({ id: 'exp-1' })));
      fixture.detectChanges();
      const c = component.form.controls;
      expect([c.amount.disabled, c.expenseDate.disabled, c.categoryId.disabled, c.paymentMethod.disabled]).toEqual([true, true, true, true]);
      expect(c.description.enabled).toBeTrue();
      expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="posted-lock"]')).not.toBeNull();
      expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="accounting-block"]')).toBeNull();
      expect(api.postingOptions).not.toHaveBeenCalled();
      c.description.setValue('Nueva');
      component.onSubmit();
      expect(api.update).toHaveBeenCalledWith('exp-1', jasmine.objectContaining({ description: 'Nueva', amount: '120.50' }));
    });

    it('keeps the current category as "(inactiva)" when it was deactivated (AC-22)', async () => {
      await setup('exp-1');
      api.get.and.returnValue(of(makeExpense({ id: 'exp-1', category: { id: 'cat-old', name: 'Vieja', active: false } })));
      fixture.detectChanges();
      expect(component.categoryOptions[0]).toEqual({ id: 'cat-old', label: 'Vieja (inactiva)' });
      expect(component.categoryOptions.length).toBe(3);
      expect(component.form.controls.categoryId.value).toBe('cat-old');
      expect(component.form.valid).toBeTrue();
    });

    it('redirects a voided expense to its detail with a warning (AC-22)', async () => {
      await setup('exp-1');
      api.get.and.returnValue(of(makeExpense({ id: 'exp-1', status: 'VOIDED' })));
      fixture.detectChanges();
      expect(toastr.warning).toHaveBeenCalled();
      expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/expenses', 'exp-1']);
    });

    it('goes back to the list when the expense does not exist', async () => {
      await setup('nope');
      api.get.and.returnValue(throwError(() => new ExpensesApiError('Gasto no encontrado.', 404)));
      fixture.detectChanges();
      expect(toastr.error).toHaveBeenCalledWith('Gasto no encontrado.');
      expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/expenses']);
    });
  });
});
