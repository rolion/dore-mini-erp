import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Params, Router, RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { EMPTY, Subject, catchError, finalize, switchMap } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { AccountingApiError } from '../../models/accounting';
import {
  BalanceSheet,
  BalanceSheetFilters,
  BalanceSheetSection,
  EMPTY_BALANCE_SHEET_FILTERS,
  hasActiveBalanceSheetFilters,
  isBalanceSheetEmpty,
  isBalanceSheetRangeInvalid,
  isNegativeAmount,
  isZeroAmount,
} from '../../models/balance-sheet';
import { BalanceSheetApiService } from '../../services/balance-sheet-api.service';

export function balanceSheetFiltersFromParams(params: { get(name: string): string | null }): BalanceSheetFilters {
  return { dateFrom: params.get('date_from') ?? '', dateTo: params.get('date_to') ?? '' };
}

export function balanceSheetFiltersToQuery(filters: BalanceSheetFilters): Params {
  const query: Params = {};
  if (filters.dateFrom) query['date_from'] = filters.dateFrom;
  if (filters.dateTo) query['date_to'] = filters.dateTo;
  return query;
}

/** Contabilidad › Balance general: Activo, Pasivo y Patrimonio sobre el libro de asientos (solo lectura). */
@Component({
  selector: 'app-balance-sheet',
  templateUrl: './balance-sheet.component.html',
  styleUrl: './balance-sheet.component.scss',
  imports: [TranslatePipe, RouterLink, ReactiveFormsModule, MoneyPipe],
})
export class BalanceSheetComponent implements OnInit {
  sheet: BalanceSheet | null = null;
  loading = false;
  errorMessage = '';
  filters: BalanceSheetFilters = EMPTY_BALANCE_SHEET_FILTERS;
  rangeInvalid = false;

  readonly filterForm = inject(FormBuilder).nonNullable.group({ dateFrom: '', dateTo: '' });
  readonly isNegative = isNegativeAmount;

  private api = inject(BalanceSheetApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  get filtersActive(): boolean {
    return hasActiveBalanceSheetFilters(this.filters);
  }

  get empty(): boolean {
    return !this.loading && !this.errorMessage && !!this.sheet && isBalanceSheetEmpty(this.sheet) && !this.hasUnclassified;
  }

  get hasUnclassified(): boolean {
    return !!this.sheet && !isZeroAmount(this.sheet.totals.unclassifiedBalance);
  }

  get appliedFilters(): string[] {
    const applied: string[] = [];
    if (this.filters.dateFrom) applied.push(`${tr('COMMON.DESDE')}: ${this.filters.dateFrom}`);
    if (this.filters.dateTo) applied.push(`${tr('COMMON.HASTA')}: ${this.filters.dateTo}`);
    return applied;
  }

  ngOnInit(): void {
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
      .subscribe((sheet) => (this.sheet = sheet));

    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      this.filters = balanceSheetFiltersFromParams(params);
      this.filterForm.setValue(this.filters, { emitEvent: false });
      this.rangeInvalid = isBalanceSheetRangeInvalid(this.filters);
      if (this.rangeInvalid) {
        this.sheet = null;
      } else {
        this.reload$.next();
      }
    });

    this.filterForm.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.apply());
  }

  clearFilters(): void {
    this.filterForm.reset(EMPTY_BALANCE_SHEET_FILTERS);
  }

  retry(): void {
    this.reload$.next();
  }

  sectionLabel(section: BalanceSheetSection): string {
    return tr(`ACCOUNTING.BALANCE_SHEET.SECCION_${section.key}`);
  }

  private apply(): void {
    void this.router.navigate([], { relativeTo: this.route, queryParams: balanceSheetFiltersToQuery(this.filterForm.getRawValue()) });
  }
}
