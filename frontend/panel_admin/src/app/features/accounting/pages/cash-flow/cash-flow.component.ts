import { DatePipe } from '@angular/common';
import { Component, DestroyRef, ElementRef, OnInit, inject, viewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Params, Router, RouterLink } from '@angular/router';
import { NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { EMPTY, Subject, catchError, finalize, switchMap } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { CompactViewportService } from '../../../../core/layout/compact-viewport.service';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { AccountingApiError } from '../../models/accounting';
import {
  CashFlow,
  CashFlowFilters,
  CashFlowMovement,
  MOVEMENT_TYPES,
  MovementKind,
  MovementTotals,
  MovementType,
  currentMonthRange,
  isCashFlowRangeInvalid,
} from '../../models/cash-flow';
import { journalOriginLink } from '../../models/journal';
import { CashFlowApiService } from '../../services/cash-flow-api.service';

const PATH = '/pocketbiz/accounting/cash-flow';
const PAGE_SIZE = 20;

export function cashFlowFiltersFromParams(params: { get(name: string): string | null }): CashFlowFilters {
  const type = params.get('type');
  const fallback = currentMonthRange();
  return {
    dateFrom: params.get('date_from') ?? fallback.dateFrom,
    dateTo: params.get('date_to') ?? fallback.dateTo,
    accountId: params.get('account') ?? '',
    type: MOVEMENT_TYPES.includes(type as MovementType) ? (type as MovementType) : '',
  };
}

export function cashFlowFiltersToQuery(filters: CashFlowFilters, page = 0): Params {
  const query: Params = { date_from: filters.dateFrom, date_to: filters.dateTo };
  if (filters.accountId) query['account'] = filters.accountId;
  if (filters.type) query['type'] = filters.type;
  if (page > 0) query['page'] = page + 1;
  return query;
}

const KIND_CLASSES: Record<MovementKind, string> = {
  inflow: 'col-green',
  outflow: 'col-red',
  transfer_in: 'col-blue',
  transfer_out: 'col-blue',
};

/** Contabilidad › Flujo de dinero: resumen del período, desglose por cuenta de dinero y movimientos hasta el asiento. */
@Component({
  selector: 'app-cash-flow',
  templateUrl: './cash-flow.component.html',
  styleUrl: './cash-flow.component.scss',
  imports: [TranslatePipe, RouterLink, ReactiveFormsModule, DatePipe, NgbPagination, MoneyPipe],
})
export class CashFlowComponent implements OnInit {
  readonly pageSize = PAGE_SIZE;
  readonly types = MOVEMENT_TYPES;
  readonly compact = inject(CompactViewportService).compact;
  flow: CashFlow | null = null;
  flowError = '';
  flowLoading = false;
  rows: CashFlowMovement[] = [];
  totals: MovementTotals | null = null;
  total = 0;
  pageIndex = 0;
  movementsError = '';
  movementsLoading = false;
  filters: CashFlowFilters = { dateFrom: '', dateTo: '', accountId: '', type: '' };
  rangeInvalid = false;
  coverageDismissed = false;
  filtersOpen = false;

  readonly filterForm = inject(FormBuilder).nonNullable.group({ dateFrom: '', dateTo: '', type: '' as MovementType | '' });

  private api = inject(CashFlowApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private flow$ = new Subject<void>();
  private movements$ = new Subject<void>();
  private readonly summaryEl = viewChild<ElementRef<HTMLElement>>('summary');
  private lastRange = '';

  get selectedAccountName(): string {
    return this.flow?.accounts.find((a) => a.accountId === this.filters.accountId)?.name ?? this.filters.accountId;
  }

  get shownFrom(): number {
    return this.rows.length === 0 ? 0 : this.pageIndex * PAGE_SIZE + 1;
  }

  get shownTo(): number {
    return this.pageIndex * PAGE_SIZE + this.rows.length;
  }

  get filtersActive(): boolean {
    return !!this.filters.accountId || !!this.filters.type;
  }

  get appliedFilters(): string[] {
    const applied: string[] = [];
    if (this.filters.accountId) applied.push(tr('ACCOUNTING.CASH_FLOW.ACCOUNT_CHIP', { name: this.selectedAccountName }));
    if (this.filters.type) applied.push(`${tr('ACCOUNTING.CASH_FLOW.TYPE')}: ${this.typeLabel(this.filters.type)}`);
    return applied;
  }

  ngOnInit(): void {
    this.flow$
      .pipe(
        switchMap(() => {
          this.flowLoading = true;
          this.flowError = '';
          return this.api.summary(this.filters.dateFrom, this.filters.dateTo).pipe(
            catchError((err: AccountingApiError) => {
              this.flowError = err.message;
              return EMPTY;
            }),
            finalize(() => (this.flowLoading = false)),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((flow) => (this.flow = flow));

    this.movements$
      .pipe(
        switchMap(() => {
          this.movementsLoading = true;
          this.movementsError = '';
          return this.api.movements(this.filters, this.pageIndex + 1, PAGE_SIZE).pipe(
            catchError((err: AccountingApiError) => {
              this.movementsError = err.message;
              return EMPTY;
            }),
            finalize(() => (this.movementsLoading = false)),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((page) => {
        this.rows = page.results;
        this.total = page.count;
        this.totals = page.totals;
      });

    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      this.filters = cashFlowFiltersFromParams(params);
      const page = Number(params.get('page'));
      this.pageIndex = Number.isInteger(page) && page > 1 ? page - 1 : 0;
      this.rangeInvalid = false;
      this.filterForm.setValue({ dateFrom: this.filters.dateFrom, dateTo: this.filters.dateTo, type: this.filters.type }, { emitEvent: false });
      const range = `${this.filters.dateFrom}|${this.filters.dateTo}`;
      if (range !== this.lastRange) {
        this.lastRange = range;
        this.coverageDismissed = false;
        this.flow$.next();
      }
      this.movements$.next();
    });
  }

  applyForm(): void {
    const { dateFrom, dateTo, type } = this.filterForm.getRawValue();
    const next: CashFlowFilters = { dateFrom, dateTo, type, accountId: this.filters.accountId };
    this.rangeInvalid = isCashFlowRangeInvalid(next);
    if (this.rangeInvalid) return;
    void this.router.navigate([PATH], { queryParams: cashFlowFiltersToQuery(next) });
  }

  applyAndClose(): void {
    this.applyForm();
    if (this.rangeInvalid) return;
    this.filtersOpen = false;
    queueMicrotask(() => this.summaryEl()?.nativeElement.focus());
  }

  /** Elegir la cuenta (o quitar la elección si ya estaba) filtra el detalle de movimientos. */
  selectAccount(accountId: string): void {
    const next = { ...this.filters, accountId: this.filters.accountId === accountId ? '' : accountId };
    void this.router.navigate([PATH], { queryParams: cashFlowFiltersToQuery(next) });
  }

  clearFilters(): void {
    this.filtersOpen = false;
    void this.router.navigate([PATH], { queryParams: cashFlowFiltersToQuery({ ...this.filters, accountId: '', type: '' }) });
  }

  retryFlow(): void {
    this.flow$.next();
  }

  retryMovements(): void {
    this.movements$.next();
  }

  onPage(page: number): void {
    if (page - 1 === this.pageIndex) return;
    void this.router.navigate([PATH], { queryParams: cashFlowFiltersToQuery(this.filters, page - 1) });
    queueMicrotask(() => this.summaryEl()?.nativeElement.focus());
  }

  typeLabel(type: MovementType): string {
    return tr(`ACCOUNTING.CASH_FLOW.TYPE_${type.toUpperCase()}`);
  }

  kindLabel(kind: MovementKind): string {
    return tr(`ACCOUNTING.CASH_FLOW.KIND_${kind.toUpperCase()}`);
  }

  kindClass(kind: MovementKind): string {
    return KIND_CLASSES[kind];
  }

  /** Signo visible además del color: entradas y transferencias recibidas suman; salidas y enviadas restan. */
  sign(kind: MovementKind): string {
    return kind === 'inflow' || kind === 'transfer_in' ? '+' : '−';
  }

  originLink(movement: CashFlowMovement): string[] | null {
    return journalOriginLink(movement.origin);
  }

  coverageMessage(): string {
    const [y, m, d] = (this.flow?.cutoffDate ?? '').split('-');
    return tr('ACCOUNTING.CASH_FLOW.COVERAGE_PARTIAL', { date: this.flow?.cutoffDate ? `${d}/${m}/${y}` : '' });
  }
}
