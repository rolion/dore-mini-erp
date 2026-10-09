import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { NgSelectComponent } from '@ng-select/ng-select';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { ExpensesApiError } from '../../models/api-error';
import { toIsoDate } from '../../models/date-range';
import {
  DESCRIPTION_MAX_LENGTH,
  Expense,
  ExpenseInput,
  NOTES_MAX_LENGTH,
  PAYMENT_METHODS,
  PAYMENT_METHOD_LABELS,
  PaymentMethod,
  SUPPLIER_MAX_LENGTH,
  isVoided,
} from '../../models/expense';
import { CategoriesApiService } from '../../services/categories-api.service';
import { ExpensesApiService } from '../../services/expenses-api.service';

export type FormField = keyof ExpenseInput;

/** Opción del selector de categoría; la categoría actual de un gasto puede estar inactiva. */
export interface CategoryOption {
  id: string;
  label: string;
}

const AMOUNT_PATTERN = /^\d+(\.\d{1,2})?$/;
export const NO_CATEGORIES_MESSAGE = 'Primero crea una categoría';

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

/** Monto decimal con hasta 2 decimales y mayor a cero (el servidor vuelve a validarlo). */
function positiveAmount(control: AbstractControl<string>): ValidationErrors | null {
  const value = control.value.trim();
  if (!value) {
    return { required: true };
  }
  if (!AMOUNT_PATTERN.test(value)) {
    return { pattern: true };
  }
  return Number(value) > 0 ? null : { min: true };
}

@Component({
  selector: 'app-expense-form',
  templateUrl: './expense-form.component.html',
  imports: [ReactiveFormsModule, RouterLink, NgSelectComponent],
})
export class ExpenseFormComponent implements OnInit {
  readonly descriptionMaxLength = DESCRIPTION_MAX_LENGTH;
  readonly supplierMaxLength = SUPPLIER_MAX_LENGTH;
  readonly notesMaxLength = NOTES_MAX_LENGTH;
  readonly paymentMethods = PAYMENT_METHODS;
  readonly paymentLabels = PAYMENT_METHOD_LABELS;
  readonly noCategoriesMessage = NO_CATEGORIES_MESSAGE;
  readonly form = inject(FormBuilder).nonNullable.group({
    description: ['', [notBlank, Validators.maxLength(DESCRIPTION_MAX_LENGTH)]],
    amount: ['', [positiveAmount]],
    expenseDate: ['', [Validators.required]],
    categoryId: ['', [Validators.required]],
    paymentMethod: ['CASH' as PaymentMethod, [Validators.required]],
    supplierName: ['', [Validators.maxLength(SUPPLIER_MAX_LENGTH)]],
    notes: ['', [Validators.maxLength(NOTES_MAX_LENGTH)]],
  });

  expenseId: string | null = null;
  saving = false;
  loading = false;
  categoryOptions: CategoryOption[] = [];
  /** Errores de validación devueltos por el servidor, por campo; se limpian al editar. */
  serverErrors: Partial<Record<FormField, string>> = {};

  private api = inject(ExpensesApiService);
  private categoriesApi = inject(CategoriesApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  get isEdit(): boolean {
    return this.expenseId !== null;
  }

  /** Sin categorías activas no se puede registrar un gasto nuevo (al editar siempre queda la actual). */
  get noCategories(): boolean {
    return !this.loading && this.categoryOptions.length === 0;
  }

  ngOnInit(): void {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => (this.serverErrors = {}));
    this.expenseId = this.route.snapshot.paramMap.get('id');
    this.loading = true;
    this.categoriesApi
      .list({ active: true, pageSize: 100 })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (page) => {
          this.categoryOptions = page.results.map((category) => ({ id: category.id, label: category.name }));
          this.afterCategoriesLoaded();
        },
        error: (err: ExpensesApiError) => {
          this.loading = false;
          this.toastr.error(err.message);
        },
      });
  }

  hasError(field: FormField): boolean {
    const control = this.form.controls[field];
    return (control.invalid && (control.touched || control.dirty)) || !!this.serverErrors[field];
  }

  onSubmit(): void {
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    const input: ExpenseInput = {
      description: value.description.trim(),
      amount: value.amount.trim(),
      categoryId: value.categoryId,
      expenseDate: value.expenseDate,
      paymentMethod: value.paymentMethod,
      supplierName: value.supplierName.trim(),
      notes: value.notes.trim(),
    };
    this.saving = true;
    const request = this.expenseId ? this.api.update(this.expenseId, input) : this.api.create(input);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (expense) => {
        this.saving = false;
        this.toastr.success(this.isEdit ? 'Gasto actualizado' : 'Gasto registrado');
        this.router.navigate(['/expenses', expense.id]);
      },
      error: (err: ExpensesApiError) => {
        this.saving = false;
        this.showServerError(err);
      },
    });
  }

  private afterCategoriesLoaded(): void {
    if (!this.expenseId) {
      this.form.patchValue({ expenseDate: toIsoDate(new Date()) });
      this.loading = false;
      return;
    }
    this.api
      .get(this.expenseId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (expense) => this.fill(expense),
        error: (err: ExpensesApiError) => {
          this.loading = false;
          this.toastr.error(err.message);
          this.router.navigate(['/expenses']);
        },
      });
  }

  private fill(expense: Expense): void {
    if (isVoided(expense)) {
      this.loading = false;
      this.toastr.warning('El gasto está anulado y no se puede editar.');
      this.router.navigate(['/expenses', expense.id]);
      return;
    }
    // La categoría actual se conserva aunque esté inactiva (REQ-EXP-006); las demás opciones son solo activas.
    if (!this.categoryOptions.some((option) => option.id === expense.category.id)) {
      const label = expense.category.active ? expense.category.name : `${expense.category.name} (inactiva)`;
      this.categoryOptions = [{ id: expense.category.id, label }, ...this.categoryOptions];
    }
    this.form.setValue({
      description: expense.description,
      amount: expense.amount,
      expenseDate: expense.expenseDate,
      categoryId: expense.category.id,
      paymentMethod: expense.paymentMethod,
      supplierName: expense.supplierName,
      notes: expense.notes,
    });
    this.serverErrors = {};
    this.loading = false;
  }

  private showServerError(err: ExpensesApiError): void {
    const errors: Partial<Record<FormField, string>> = {};
    for (const field of Object.keys(this.form.controls) as FormField[]) {
      const messages = err.fieldErrors[field];
      if (messages?.length) {
        errors[field] = messages.join(' ');
      }
    }
    this.serverErrors = errors;
    if (!Object.keys(errors).length) {
      this.toastr.error(err.message);
    }
  }
}
