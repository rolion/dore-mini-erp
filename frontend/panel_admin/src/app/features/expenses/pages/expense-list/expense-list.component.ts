import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { ToastrService } from 'ngx-toastr';
import { EMPTY, Subject, catchError, finalize, switchMap } from 'rxjs';
import Swal from 'sweetalert2';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { ExpensesApiError } from '../../models/api-error';
import { ExpenseCategory } from '../../models/category';
import { DateRange, monthRange } from '../../models/date-range';
import {
  EXPENSE_STATUS_LABELS,
  Expense,
  ExpenseListParams,
  ExpenseStatus,
  ExpenseStatusFilter,
  PAYMENT_METHOD_LABELS,
  PaymentMethod,
  isVoided,
} from '../../models/expense';
import { CategoriesApiService } from '../../services/categories-api.service';
import { ExpensesApiService } from '../../services/expenses-api.service';

export type RangeShortcut = 'month' | 'previous-month' | 'all';

export const RANGE_SHORTCUTS: readonly { id: RangeShortcut; label: string }[] = [
  { id: 'month', label: 'Este mes' },
  { id: 'previous-month', label: 'Mes anterior' },
  { id: 'all', label: 'Todo' },
];

export const INVALID_RANGE_MESSAGE = 'La fecha final no puede ser anterior a la inicial.';

@Component({
  selector: 'app-expense-list',
  templateUrl: './expense-list.component.html',
  styleUrl: './expense-list.component.scss',
  imports: [RouterLink, NgxDatatableModule, ReactiveFormsModule, DatePipe, MoneyPipe],
})
export class ExpenseListComponent implements OnInit {
  readonly pageSize = 10;
  readonly messages = { emptyMessage: 'No hay gastos que coincidan', totalMessage: 'en total' };
  readonly shortcuts = RANGE_SHORTCUTS;
  readonly filterForm = inject(FormBuilder).nonNullable.group({
    dateFrom: [''],
    dateTo: [''],
    categoryId: [''],
    /** Los gastos anulados no aparecen por defecto (REQ-EXP-004). */
    status: ['active' as ExpenseStatusFilter],
  });

  rows: Expense[] = [];
  total = 0;
  /** Suma de los gastos vigentes del filtro (todas las páginas), calculada por el servidor. */
  totalAmount = '0.00';
  /** Página actual base 0, como espera ngx-datatable. */
  pageIndex = 0;
  loading = false;
  categories: ExpenseCategory[] = [];
  currentShortcut: RangeShortcut | null = 'month';
  rangeError = '';

  private api = inject(ExpensesApiService);
  private categoriesApi = inject(CategoriesApiService);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  readonly rowClass = (row: Expense): string => (isVoided(row) ? 'expense-voided' : '');

  get filtersActive(): boolean {
    const { dateFrom, dateTo, categoryId, status } = this.filterForm.getRawValue();
    return !!(dateFrom || dateTo || categoryId) || status !== 'active';
  }

  get showsVoided(): boolean {
    return this.filterForm.controls.status.value !== 'active';
  }

  ngOnInit(): void {
    this.reload$
      .pipe(
        switchMap(() => {
          this.loading = true;
          return this.api.list(this.params()).pipe(
            catchError((err: ExpensesApiError) => {
              this.toastr.error(err.message);
              return EMPTY;
            }),
            finalize(() => (this.loading = false)),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((page) => {
        this.rows = page.results;
        this.total = page.count;
        this.totalAmount = page.totalAmount;
      });

    this.categoriesApi
      .list({ pageSize: 100 })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (page) => (this.categories = page.results),
        error: (err: ExpensesApiError) => this.toastr.error(err.message),
      });

    this.filterForm.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.currentShortcut = this.matchingShortcut();
      this.pageIndex = 0;
      if (this.validateRange()) {
        this.reload$.next();
      }
    });

    this.applyRange(monthRange(this.today()), true);
  }

  applyShortcut(shortcut: RangeShortcut): void {
    const range =
      shortcut === 'month'
        ? monthRange(this.today())
        : shortcut === 'previous-month'
          ? monthRange(this.today(), -1)
          : { dateFrom: '', dateTo: '' };
    this.applyRange(range);
  }

  clearFilters(): void {
    this.filterForm.setValue({ dateFrom: '', dateTo: '', categoryId: '', status: 'active' });
  }

  onPage(event: { offset: number }): void {
    // ngx-datatable también emite `page` al inicializarse; sin cambio de página no se vuelve a pedir.
    if (event.offset === this.pageIndex) {
      return;
    }
    this.pageIndex = event.offset;
    this.reload$.next();
  }

  paymentLabel(method: PaymentMethod): string {
    return PAYMENT_METHOD_LABELS[method];
  }

  statusLabel(status: ExpenseStatus): string {
    return EXPENSE_STATUS_LABELS[status];
  }

  categoryLabel(category: ExpenseCategory): string {
    return category.active ? category.name : `${category.name} (inactiva)`;
  }

  async voidExpense(expense: Expense): Promise<void> {
    if (!(await this.confirmVoid(expense))) {
      return;
    }
    this.api
      .void(expense.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.toastr.success('Gasto anulado');
          this.reload$.next();
        },
        error: (err: ExpensesApiError) => this.toastr.error(err.message),
      });
  }

  /** Confirmación previa a anular; separada para poder sustituirla en pruebas. */
  protected async confirmVoid(expense: Expense): Promise<boolean> {
    const result = await Swal.fire({
      titleText: `¿Anular el gasto "${expense.description}"?`,
      text: 'Este gasto dejará de sumar en los reportes. Se conserva en el historial.',
      showCancelButton: true,
      confirmButtonColor: '#8963ff',
      cancelButtonColor: '#fb7823',
      confirmButtonText: 'Anular gasto',
      cancelButtonText: 'Cancelar',
    });
    return result.isConfirmed;
  }

  /** "Hoy" del navegador; separado para fijarlo en pruebas. */
  protected today(): Date {
    return new Date();
  }

  private applyRange(range: DateRange, silent = false): void {
    this.filterForm.patchValue(range, { emitEvent: !silent });
    if (silent) {
      this.currentShortcut = this.matchingShortcut();
      this.reload$.next();
    }
  }

  private matchingShortcut(): RangeShortcut | null {
    const { dateFrom, dateTo } = this.filterForm.getRawValue();
    const candidates: [RangeShortcut, DateRange][] = [
      ['month', monthRange(this.today())],
      ['previous-month', monthRange(this.today(), -1)],
      ['all', { dateFrom: '', dateTo: '' }],
    ];
    const match = candidates.find(([, range]) => range.dateFrom === dateFrom && range.dateTo === dateTo);
    return match ? match[0] : null;
  }

  private validateRange(): boolean {
    const { dateFrom, dateTo } = this.filterForm.getRawValue();
    this.rangeError = dateFrom && dateTo && dateFrom > dateTo ? INVALID_RANGE_MESSAGE : '';
    return !this.rangeError;
  }

  private params(): ExpenseListParams {
    const { dateFrom, dateTo, categoryId, status } = this.filterForm.getRawValue();
    return {
      dateFrom: dateFrom || undefined,
      dateTo: dateTo || undefined,
      categoryId: categoryId || undefined,
      status,
      page: this.pageIndex + 1,
      pageSize: this.pageSize,
    };
  }
}
