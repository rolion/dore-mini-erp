import { tr } from '../../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import Swal from 'sweetalert2';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { ExpensesApiError } from '../../models/api-error';
import { EXPENSE_STATUS_LABELS, Expense, PAYMENT_METHOD_LABELS, isVoided } from '../../models/expense';
import { ExpensesApiService } from '../../services/expenses-api.service';

@Component({
  selector: 'app-expense-detail',
  templateUrl: './expense-detail.component.html',
  imports: [TranslatePipe, RouterLink, DatePipe, MoneyPipe],
})
export class ExpenseDetailComponent implements OnInit {
  readonly paymentLabels = PAYMENT_METHOD_LABELS;
  readonly statusLabels = EXPENSE_STATUS_LABELS;

  expense: Expense | null = null;
  loading = true;

  private api = inject(ExpensesApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  get voided(): boolean {
    return this.expense !== null && isVoided(this.expense);
  }

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    this.api
      .get(id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (expense) => {
          this.expense = expense;
          this.loading = false;
        },
        error: (err: ExpensesApiError) => {
          this.loading = false;
          this.toastr.error(err.message);
          this.router.navigate(['/pocketbiz/expenses']);
        },
      });
  }

  async voidExpense(): Promise<void> {
    const expense = this.expense;
    if (!expense || !(await this.confirmVoid(expense))) {
      return;
    }
    this.api
      .void(expense.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (updated) => {
          this.expense = updated;
          this.toastr.success(tr('EXPENSES.EXPENSE_DETAIL.GASTO_ANULADO'));
        },
        error: (err: ExpensesApiError) => this.toastr.error(err.message),
      });
  }

  /** Confirmación previa a anular; separada para poder sustituirla en pruebas. */
  protected async confirmVoid(expense: Expense): Promise<boolean> {
    const result = await Swal.fire({
      titleText: tr('EXPENSES.EXPENSE_DETAIL.ANULAR_EL_GASTO', { p0: expense.description }),
      text: tr('EXPENSES.EXPENSE_DETAIL.ESTE_GASTO_DEJARA_DE_SUMAR'),
      showCancelButton: true,
      confirmButtonColor: '#8963ff',
      cancelButtonColor: '#fb7823',
      confirmButtonText: tr('EXPENSES.EXPENSE_DETAIL.ANULAR_GASTO_2'),
      cancelButtonText: tr('CUSTOMERS.CUSTOMER_QUICK_CREATE.CANCELAR'),
    });
    return result.isConfirmed;
  }
}
