import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Params, Router, RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { EMPTY, Subject, catchError, finalize, switchMap } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { ACCOUNT_CLASSES, Account, AccountClassCode, AccountingApiError } from '../../models/accounting';
import {
  BalanceFilters,
  BalanceRow,
  Balances,
  EMPTY_BALANCE_FILTERS,
  hasActiveBalanceFilters,
  isBalanceRangeInvalid,
} from '../../models/balances';
import { FiscalPeriod } from '../../models/fiscal-period';
import { AccountingApiService } from '../../services/accounting-api.service';
import { BalancesApiService } from '../../services/balances-api.service';
import { FiscalPeriodsApiService } from '../../services/fiscal-periods-api.service';

const JOURNAL_PATH = '/pocketbiz/accounting/journal';

export function balanceFiltersFromParams(params: { get(name: string): string | null }): BalanceFilters {
  const accountClass = params.get('account_class');
  return {
    dateFrom: params.get('date_from') ?? '',
    dateTo: params.get('date_to') ?? '',
    accountClass: ACCOUNT_CLASSES.includes(accountClass as AccountClassCode) ? (accountClass as AccountClassCode) : '',
    accountId: params.get('account_id') ?? '',
  };
}

export function balanceFiltersToQuery(filters: BalanceFilters): Params {
  const query: Params = {};
  if (filters.dateFrom) query['date_from'] = filters.dateFrom;
  if (filters.dateTo) query['date_to'] = filters.dateTo;
  if (filters.accountClass) query['account_class'] = filters.accountClass;
  if (filters.accountId) query['account_id'] = filters.accountId;
  return query;
}

/** Contabilidad › Saldos: sumas y saldos de todas las cuentas sobre el libro de asientos (solo lectura). */
@Component({
  selector: 'app-balances-page',
  templateUrl: './balances-page.component.html',
  imports: [TranslatePipe, RouterLink, ReactiveFormsModule],
})
export class BalancesPageComponent implements OnInit {
  readonly classes = ACCOUNT_CLASSES;
  balances: Balances | null = null;
  loading = false;
  errorMessage = '';
  filters: BalanceFilters = EMPTY_BALANCE_FILTERS;
  rangeInvalid = false;
  accounts: Account[] = [];
  periods: FiscalPeriod[] = [];
  periodId = '';

  readonly filterForm = inject(FormBuilder).nonNullable.group({
    dateFrom: '',
    dateTo: '',
    accountClass: '' as AccountClassCode | '',
    accountId: '',
  });

  private api = inject(BalancesApiService);
  private accountingApi = inject(AccountingApiService);
  private periodsApi = inject(FiscalPeriodsApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  get rows(): BalanceRow[] {
    return this.balances?.rows ?? [];
  }

  get filtersActive(): boolean {
    return hasActiveBalanceFilters(this.filters);
  }

  get empty(): boolean {
    return !this.loading && !this.errorMessage && !!this.balances && this.rows.length === 0;
  }

  get appliedFilters(): string[] {
    const f = this.filters;
    const applied: string[] = [];
    if (f.dateFrom) applied.push(`${tr('COMMON.DESDE')}: ${f.dateFrom}`);
    if (f.dateTo) applied.push(`${tr('COMMON.HASTA')}: ${f.dateTo}`);
    if (f.accountClass) applied.push(`${tr('ACCOUNTING.BALANCES.CLASIFICACION')}: ${this.classLabel(f.accountClass)}`);
    if (f.accountId) applied.push(`${tr('ACCOUNTING.BALANCES.CUENTA')}: ${this.accountName(f.accountId)}`);
    return applied;
  }

  ngOnInit(): void {
    this.accountingApi.listAccounts().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (accounts) => (this.accounts = accounts),
      error: () => undefined, // el filtro de cuenta queda vacío; los saldos siguen funcionando
    });
    this.periodsApi.list().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (periods) => (this.periods = periods),
      error: () => undefined,
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
      .subscribe((balances) => (this.balances = balances));

    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      this.filters = balanceFiltersFromParams(params);
      this.filterForm.setValue(this.filters, { emitEvent: false });
      this.rangeInvalid = isBalanceRangeInvalid(this.filters);
      if (this.rangeInvalid) {
        this.balances = null;
      } else {
        this.reload$.next();
      }
    });

    this.filterForm.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.apply());
  }

  /** Elegir un período rellena Desde/Hasta con sus límites. */
  onPeriod(id: string): void {
    this.periodId = id;
    const period = this.periods.find((p) => p.id === id);
    this.filterForm.patchValue({ dateFrom: period?.startDate ?? '', dateTo: period?.endDate ?? '' });
  }

  clearFilters(): void {
    this.periodId = '';
    this.filterForm.reset(EMPTY_BALANCE_FILTERS);
  }

  retry(): void {
    this.reload$.next();
  }

  classLabel(code: AccountClassCode | null): string {
    return code ? tr(`ACCOUNTING.ACCOUNT_CLASSES.${code}`) : tr('ACCOUNTING.BALANCES.SIN_CLASIFICAR');
  }

  /** Movimientos de la cuenta con el mismo rango de fechas. */
  movementsQuery(row: BalanceRow): Params {
    const query: Params = { account_id: row.accountId };
    if (this.filters.dateFrom) query['date_from'] = this.filters.dateFrom;
    if (this.filters.dateTo) query['date_to'] = this.filters.dateTo;
    return query;
  }

  readonly journalPath = JOURNAL_PATH;

  private accountName(id: string): string {
    return this.accounts.find((account) => account.id === id)?.name ?? id;
  }

  private apply(): void {
    this.periodId = this.matchingPeriod();
    void this.router.navigate([], { relativeTo: this.route, queryParams: balanceFiltersToQuery(this.filterForm.getRawValue()) });
  }

  private matchingPeriod(): string {
    const { dateFrom, dateTo } = this.filterForm.getRawValue();
    return this.periods.find((p) => p.startDate === dateFrom && p.endDate === dateTo)?.id ?? '';
  }
}
