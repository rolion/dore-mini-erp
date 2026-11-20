import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Params, Router, RouterLink } from '@angular/router';
import { NgSelectComponent } from '@ng-select/ng-select';
import { TranslatePipe } from '@ngx-translate/core';
import { EMPTY, Subject, catchError, finalize, switchMap } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { AccountingApiError } from '../../models/accounting';
import { FiscalPeriod } from '../../models/fiscal-period';
import {
  IncomeExpenseFilters,
  IncomeExpenseMonth,
  IncomeExpenseReport,
  IncomeExpenseSort,
  IncomeExpenseSortKey,
  isLoss,
  monthKeysBetween,
  nextSort,
  sortMonths,
} from '../../models/income-expense';
import { FiscalPeriodsApiService } from '../../services/fiscal-periods-api.service';
import { IncomeExpenseApiService } from '../../services/income-expense-api.service';

const MONTH_PATTERN = /^\d{4}-(0[1-9]|1[0-2])$/;

export function incomeExpenseFiltersFromParams(params: { get(name: string): string | null }): IncomeExpenseFilters {
  const months = (params.get('months') ?? '').split(',').filter((m) => MONTH_PATTERN.test(m));
  return { periodId: params.get('period') ?? '', months };
}

export function incomeExpenseFiltersToQuery(filters: IncomeExpenseFilters): Params {
  const query: Params = {};
  if (filters.periodId) query['period'] = filters.periodId;
  if (filters.months.length > 0) query['months'] = filters.months.join(',');
  return query;
}

export interface MonthOption {
  id: string;
  label: string;
}

/** Contabilidad › Ingresos y egresos: suma por mes de un período fiscal (solo lectura sobre el libro de asientos). */
@Component({
  selector: 'app-income-expense',
  templateUrl: './income-expense.component.html',
  imports: [TranslatePipe, RouterLink, ReactiveFormsModule, NgSelectComponent, MoneyPipe],
})
export class IncomeExpenseComponent implements OnInit {
  report: IncomeExpenseReport | null = null;
  loading = false;
  errorMessage = '';
  filters: IncomeExpenseFilters = { periodId: '', months: [] };
  periods: FiscalPeriod[] = [];
  sort: IncomeExpenseSort | null = null;

  readonly filterForm = inject(FormBuilder).nonNullable.group({ periodId: '', months: [[] as string[]] });

  private api = inject(IncomeExpenseApiService);
  private periodsApi = inject(FiscalPeriodsApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  get rows(): IncomeExpenseMonth[] {
    return sortMonths(this.report?.months ?? [], this.sort);
  }

  get noPeriods(): boolean {
    return !this.loading && !this.errorMessage && !!this.report && this.report.period === null;
  }

  get filtersActive(): boolean {
    return !!this.filters.periodId || this.filters.months.length > 0;
  }

  /** Período mostrado: el elegido o, sin elección, el que eligió el servidor. */
  get selectedPeriodId(): string {
    return this.filters.periodId || this.report?.period?.id || '';
  }

  get monthOptions(): MonthOption[] {
    const period = this.report?.period;
    const chosen = this.periods.find((p) => p.id === this.selectedPeriodId);
    const from = chosen?.startDate ?? period?.dateFrom;
    const to = chosen?.endDate ?? period?.dateTo;
    return from && to ? monthKeysBetween(from, to).map((id) => ({ id, label: this.monthLabel(id) })) : [];
  }

  ngOnInit(): void {
    this.periodsApi.list().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (periods) => (this.periods = periods),
      error: () => undefined, // el selector queda con el período mostrado; el reporte sigue funcionando
    });

    this.reload$
      .pipe(
        switchMap(() => {
          this.loading = true;
          this.errorMessage = '';
          return this.api.get(this.filters).pipe(
            catchError((err: AccountingApiError) => {
              this.errorMessage = err.message;
              return EMPTY;
            }),
            finalize(() => (this.loading = false)),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((report) => {
        this.report = report;
        this.filterForm.patchValue({ periodId: this.selectedPeriodId }, { emitEvent: false });
      });

    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      this.filters = incomeExpenseFiltersFromParams(params);
      this.filterForm.setValue({ periodId: this.filters.periodId, months: this.filters.months }, { emitEvent: false });
      this.reload$.next();
    });
  }

  onPeriod(periodId: string): void {
    this.navigate({ periodId, months: [] });
  }

  onMonths(months: string[]): void {
    this.navigate({ periodId: this.filters.periodId || this.selectedPeriodId, months: months ?? [] });
  }

  clearFilters(): void {
    this.navigate({ periodId: '', months: [] });
  }

  retry(): void {
    this.reload$.next();
  }

  sortBy(key: IncomeExpenseSortKey): void {
    this.sort = nextSort(this.sort, key);
  }

  ariaSort(key: IncomeExpenseSortKey): 'ascending' | 'descending' | 'none' {
    if (this.sort?.key !== key) return 'none';
    return this.sort.direction === 'asc' ? 'ascending' : 'descending';
  }

  sortIcon(key: IncomeExpenseSortKey): string {
    if (this.sort?.key !== key) return 'fa-sort';
    return this.sort.direction === 'asc' ? 'fa-sort-up' : 'fa-sort-down';
  }

  isLoss(profit: string): boolean {
    return isLoss(profit);
  }

  monthLabel(key: string): string {
    return `${tr(`ACCOUNTING.INCOME_EXPENSE.MONTH_${key.slice(5, 7)}`)} ${key.slice(0, 4)}`;
  }

  private navigate(filters: IncomeExpenseFilters): void {
    void this.router.navigate([], { relativeTo: this.route, queryParams: incomeExpenseFiltersToQuery(filters) });
  }
}
