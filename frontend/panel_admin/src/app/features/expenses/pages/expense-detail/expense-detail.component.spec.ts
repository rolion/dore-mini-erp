import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { ExpensesApiError } from '../../models/api-error';
import { Expense } from '../../models/expense';
import { ExpensesApiService } from '../../services/expenses-api.service';
import { makeExpense } from '../../testing/expense-fixtures';
import { ExpenseDetailComponent } from './expense-detail.component';

interface Hooks {
  confirmVoid(expense: Expense): Promise<boolean>;
}

describe('ExpenseDetailComponent', () => {
  let fixture: ComponentFixture<ExpenseDetailComponent>;
  let component: ExpenseDetailComponent;
  let api: jasmine.SpyObj<ExpensesApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let router: Router;

  beforeEach(async () => {
    api = jasmine.createSpyObj<ExpensesApiService>('ExpensesApiService', ['get', 'void']);
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    await TestBed.configureTestingModule({
      imports: [ExpenseDetailComponent],
      providers: [
        provideRouter([]),
        { provide: ExpensesApiService, useValue: api },
        { provide: ToastrService, useValue: toastr },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'exp-1' }) } } },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(ExpenseDetailComponent);
    component = fixture.componentInstance;
  });

  const text = () => (fixture.nativeElement as HTMLElement).textContent ?? '';
  const buttons = () =>
    fixture.debugElement.queryAll(By.css('.btn')).map((b) => (b.nativeElement as HTMLElement).textContent?.trim());

  it('shows every field, including the payment method and the inactive category (AC-23)', () => {
    api.get.and.returnValue(
      of(makeExpense({ paymentMethod: 'BANK_TRANSFER', category: { id: 'c', name: 'Vieja', active: false } })),
    );
    fixture.detectChanges();
    expect(api.get).toHaveBeenCalledWith('exp-1');
    const method = fixture.debugElement.query(By.css('[data-testid="payment-method"]')).nativeElement as HTMLElement;
    expect(method.textContent?.trim()).toBe('Transferencia');
    expect(text()).toContain('Harina de maíz');
    expect(text()).toContain('Bs 120.50');
    expect(text()).toContain('05/10/2026');
    expect(text()).toContain('Vieja');
    expect(text()).toContain('(inactiva)');
    expect(text()).toContain('Molino Sur');
    expect(text()).toContain('Vigente');
    expect(buttons()).toEqual(['Editar', 'Anular gasto', 'Volver']);
  });

  it('shows dashes for empty supplier and notes', () => {
    api.get.and.returnValue(of(makeExpense({ supplierName: '', notes: '' })));
    fixture.detectChanges();
    expect(text()).toContain('—');
    expect(text()).toContain('Sin notas');
  });

  it('shows a voided expense with its badge and without edit or void (AC-23)', () => {
    api.get.and.returnValue(of(makeExpense({ status: 'VOIDED', voidedAt: '2026-10-06T10:00:00Z' })));
    fixture.detectChanges();
    expect(text()).toContain('Anulado');
    expect(buttons()).toEqual(['Volver']);
  });

  it('voids after confirming and then hides the actions (AC-23)', async () => {
    api.get.and.returnValue(of(makeExpense()));
    api.void.and.returnValue(of(makeExpense({ status: 'VOIDED', voidedAt: '2026-10-06T10:00:00Z' })));
    spyOn(component as unknown as Hooks, 'confirmVoid').and.resolveTo(true);
    fixture.detectChanges();
    await component.voidExpense();
    fixture.detectChanges();
    expect(api.void).toHaveBeenCalledWith('exp-1');
    expect(toastr.success).toHaveBeenCalledWith('Gasto anulado');
    expect(component.voided).toBeTrue();
    expect(buttons()).toEqual(['Volver']);
  });

  it('does not void when the confirmation is cancelled (AC-23)', async () => {
    api.get.and.returnValue(of(makeExpense()));
    spyOn(component as unknown as Hooks, 'confirmVoid').and.resolveTo(false);
    fixture.detectChanges();
    await component.voidExpense();
    expect(api.void).not.toHaveBeenCalled();
    expect(component.voided).toBeFalse();
  });

  it('shows the server message when voiding fails', async () => {
    api.get.and.returnValue(of(makeExpense()));
    api.void.and.returnValue(throwError(() => new ExpensesApiError('El gasto ya está anulado.', 409, {}, 'already_voided')));
    spyOn(component as unknown as Hooks, 'confirmVoid').and.resolveTo(true);
    fixture.detectChanges();
    await component.voidExpense();
    expect(toastr.error).toHaveBeenCalledWith('El gasto ya está anulado.');
    expect(component.voided).toBeFalse();
  });

  it('goes back to the list when the expense does not exist', () => {
    api.get.and.returnValue(throwError(() => new ExpensesApiError('Gasto no encontrado.', 404)));
    fixture.detectChanges();
    expect(toastr.error).toHaveBeenCalledWith('Gasto no encontrado.');
    expect(router.navigate).toHaveBeenCalledWith(['/expenses']);
  });
});
