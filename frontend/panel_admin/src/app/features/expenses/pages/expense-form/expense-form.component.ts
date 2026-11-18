import { tr } from '../../../../core/i18n/translate';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { issueText } from '../../../accounting/models/posting-messages';
import { TranslatePipe } from '@ngx-translate/core';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { NgSelectComponent } from '@ng-select/ng-select';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { catchError, merge, of, startWith, switchMap } from 'rxjs';
import { ExpensesApiError } from '../../models/api-error';
import { toIsoDate } from '../../models/date-range';
import {
  AccountRef,
  DESCRIPTION_MAX_LENGTH,
  Expense,
  ExpenseCreateInput,
  ExpenseInput,
  NOTES_MAX_LENGTH,
  PAYMENT_METHODS,
  PAYMENT_METHOD_LABELS,
  PaymentMethod,
  PostingIssue,
  PostingOptions,
  SUPPLIER_MAX_LENGTH,
  isVoided,
} from '../../models/expense';
import { CategoriesApiService } from '../../services/categories-api.service';
import { ExpensesApiService } from '../../services/expenses-api.service';

export type FormField = keyof ExpenseInput | 'expenseAccountId' | 'paymentAccountId';

/** Opción de un selector de cuenta contable. */
export interface AccountOption {
  id: string;
  label: string;
}

export const accountLabel = (account: AccountRef): string =>
  account.code ? `${account.code} · ${account.name}` : account.name;

/** Opción del selector de categoría; la categoría actual de un gasto puede estar inactiva. */
export interface CategoryOption {
  id: string;
  label: string;
}

const AMOUNT_PATTERN = /^\d+(\.\d{1,2})?$/;
export const NO_CATEGORIES_MESSAGE = (): string => tr('EXPENSES.EXPENSE_FORM.PRIMERO_CREA_UNA_CATEGORIA');

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
  imports: [TranslatePipe, ReactiveFormsModule, RouterLink, NgSelectComponent, MoneyPipe],
})
export class ExpenseFormComponent implements OnInit {
  readonly descriptionMaxLength = DESCRIPTION_MAX_LENGTH;
  readonly supplierMaxLength = SUPPLIER_MAX_LENGTH;
  readonly notesMaxLength = NOTES_MAX_LENGTH;
  readonly paymentMethods = PAYMENT_METHODS;
  readonly paymentLabels = PAYMENT_METHOD_LABELS;
  readonly noCategoriesMessage = NO_CATEGORIES_MESSAGE();
  readonly form = inject(FormBuilder).nonNullable.group({
    description: ['', [notBlank, Validators.maxLength(DESCRIPTION_MAX_LENGTH)]],
    amount: ['', [positiveAmount]],
    expenseDate: ['', [Validators.required]],
    categoryId: ['', [Validators.required]],
    paymentMethod: ['CASH' as PaymentMethod, [Validators.required]],
    supplierName: ['', [Validators.maxLength(SUPPLIER_MAX_LENGTH)]],
    notes: ['', [Validators.maxLength(NOTES_MAX_LENGTH)]],
    // Cuentas contables elegidas; vacías = las de la configuración (valor por defecto).
    expenseAccountId: [null as string | null],
    paymentAccountId: [null as string | null],
  });

  expenseId: string | null = null;
  saving = false;
  loading = false;
  categoryOptions: CategoryOption[] = [];
  /** Cuentas por defecto y elegibles; `null` mientras carga, si falló o al editar. Sin cobertura, `covered` es false. */
  options: PostingOptions | null = null;
  expenseAccountItems: AccountOption[] = [];
  paymentAccountItems: AccountOption[] = [];
  /** Gasto contabilizado que se edita: monto, categoría, fecha y método quedan de solo lectura. */
  posted = false;
  /** Código de la última respuesta de error de contabilización (p. ej. `fiscal_period_closed`). */
  errorCode: string | null = null;
  /** Mensaje accionable de un 409 contable (período cerrado o fuera de períodos). */
  postingError = '';
  postingIssues: PostingIssue[] = [];
  /** Errores de validación devueltos por el servidor, por campo; se limpian al editar. */
  serverErrors: Partial<Record<FormField, string>> = {};

  private api = inject(ExpensesApiService);
  private categoriesApi = inject(CategoriesApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);
  /**
   * Un envío = una clave: reintentar los mismos datos no duplica el gasto ni el asiento. Si la persona cambia algún
   * dato entre intentos es un envío nuevo y la clave se renueva (así un 409 de clave reutilizada no la deja atascada).
   */
  private idempotencyKey = crypto.randomUUID();
  private lastSubmission = '';

  get isEdit(): boolean {
    return this.expenseId !== null;
  }

  /** Sin categorías activas no se puede registrar un gasto nuevo (al editar siempre queda la actual). */
  get noCategories(): boolean {
    return !this.loading && this.categoryOptions.length === 0;
  }

  /** ¿Contabilidad cubre esta fecha? Solo entonces se muestran las cuentas (alta de un gasto nuevo). */
  get covered(): boolean {
    return !this.isEdit && this.options?.covered === true;
  }

  get effectiveExpenseAccount(): AccountRef | null {
    return this.pick(this.form.controls.expenseAccountId.value, this.options?.expenseAccounts) ?? this.options?.expenseAccount ?? null;
  }

  get effectivePaymentAccount(): AccountRef | null {
    return this.pick(this.form.controls.paymentAccountId.value, this.options?.paymentAccounts) ?? this.options?.paymentAccount ?? null;
  }

  /** Con cobertura hace falta una cuenta de gasto y una de pago, elegidas o por defecto. */
  get missingAccounts(): boolean {
    return this.covered && (!this.effectiveExpenseAccount || !this.effectivePaymentAccount);
  }

  issueMessage(issue: PostingIssue): string {
    return issueText(issue);
  }

  ngOnInit(): void {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.serverErrors = {};
      this.errorCode = null;
      this.postingError = '';
      this.postingIssues = [];
    });
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
    const input: ExpenseCreateInput = {
      description: value.description.trim(),
      amount: value.amount.trim(),
      categoryId: value.categoryId,
      expenseDate: value.expenseDate,
      paymentMethod: value.paymentMethod,
      supplierName: value.supplierName.trim(),
      notes: value.notes.trim(),
    };
    if (this.covered) {
      input.expenseAccountId = value.expenseAccountId;
      input.paymentAccountId = value.paymentAccountId;
    }
    if (!this.isEdit) {
      const signature = JSON.stringify(input);
      if (this.lastSubmission && signature !== this.lastSubmission) {
        this.idempotencyKey = crypto.randomUUID();
      }
      this.lastSubmission = signature;
      input.idempotencyKey = this.idempotencyKey;
    }
    this.saving = true;
    const request = this.expenseId ? this.api.update(this.expenseId, input) : this.api.create(input);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (expense) => {
        this.saving = false;
        this.toastr.success(this.isEdit ? tr('EXPENSES.EXPENSE_FORM.GASTO_ACTUALIZADO') : tr('EXPENSES.EXPENSE_FORM.GASTO_REGISTRADO'));
        this.router.navigate(['/pocketbiz/expenses', expense.id]);
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
      this.watchPostingOptions();
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
          this.router.navigate(['/pocketbiz/expenses']);
        },
      });
  }

  private fill(expense: Expense): void {
    if (isVoided(expense)) {
      this.loading = false;
      this.toastr.warning(tr('EXPENSES.EXPENSE_FORM.EL_GASTO_ESTA_ANULADO_Y'));
      this.router.navigate(['/pocketbiz/expenses', expense.id]);
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
      expenseAccountId: null,
      paymentAccountId: null,
    });
    this.posted = expense.posted;
    if (this.posted) {
      for (const control of [this.form.controls.amount, this.form.controls.expenseDate, this.form.controls.categoryId, this.form.controls.paymentMethod]) {
        control.disable({ emitEvent: false });
      }
    }
    this.serverErrors = {};
    this.loading = false;
  }

  private pick(id: string | null, accounts: AccountRef[] | undefined): AccountRef | null {
    return id ? (accounts ?? []).find((account) => account.id === id) ?? null : null;
  }

  /** Recarga las cuentas por defecto y elegibles cuando cambian la fecha, la categoría o el método de pago. */
  private watchPostingOptions(): void {
    const controls = this.form.controls;
    merge(controls.expenseDate.valueChanges, controls.categoryId.valueChanges, controls.paymentMethod.valueChanges)
      .pipe(
        startWith(null),
        switchMap(() => {
          const { expenseDate, categoryId, paymentMethod } = this.form.getRawValue();
          if (!expenseDate) {
            return of(null);
          }
          return this.api.postingOptions(expenseDate, categoryId || null, paymentMethod).pipe(catchError(() => of(null)));
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((options) => {
        this.options = options;
        this.expenseAccountItems = (options?.expenseAccounts ?? []).map((a) => ({ id: a.id, label: accountLabel(a) }));
        this.paymentAccountItems = (options?.paymentAccounts ?? []).map((a) => ({ id: a.id, label: accountLabel(a) }));
      });
  }

  private showServerError(err: ExpensesApiError): void {
    this.errorCode = err.code;
    this.postingIssues = err.issues;
    this.postingError = err.status === 409 ? err.message : '';
    const errors: Partial<Record<FormField, string>> = {};
    for (const field of Object.keys(this.form.controls) as FormField[]) {
      const messages = err.fieldErrors[field];
      if (messages?.length) {
        errors[field] = messages.join(' ');
      }
    }
    this.serverErrors = errors;
    if (!Object.keys(errors).length && !err.issues.length && !this.postingError) {
      this.toastr.error(err.message);
    }
  }
}
