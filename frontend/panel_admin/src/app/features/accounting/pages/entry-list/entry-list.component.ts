import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { EMPTY, Subject, catchError, debounceTime, finalize, switchMap } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { Account, AccountingApiError, PaymentMethod } from '../../models/accounting';
import {
  ENTRY_ORIGINS,
  EMPTY_ENTRY_FILTERS,
  Entry,
  EntryListFilters,
  EntryOrigin,
  CurrencyTotal,
  ORIGIN_CLASSES,
  documentLabel,
  formatAmount,
  originLabel,
  sourceLink,
} from '../../models/entry';
import { AccountingApiService } from '../../services/accounting-api.service';
import { EntriesApiService } from '../../services/entries-api.service';
import { filtersFromParams, filtersToQuery, hasActiveFilters, isRangeInvalid } from './entry-list-filters';

const LIST_PATH = '/pocketbiz/accounting/entries';
const FILTER_DEBOUNCE_MS = 300;

/** Libro de entradas: cobros recibidos, solo lectura. Los filtros viven en la URL; los totales son de todo el filtro. */
@Component({
  selector: 'app-entry-list',
  templateUrl: './entry-list.component.html',
  styleUrl: './entry-list.component.scss',
  imports: [TranslatePipe, RouterLink, ReactiveFormsModule, NgxDatatableModule, DatePipe],
})
export class EntryListComponent implements OnInit {
  readonly pageSize = 20;
  readonly origins = ENTRY_ORIGINS;
  rows: Entry[] = [];
  total = 0;
  totals: CurrencyTotal[] = [];
  coverage: { firstPaymentDate: string | null; lastPaymentDate: string | null; firstRecordedAt: string | null } | null = null;
  /** Página actual base 0, como espera ngx-datatable. */
  pageIndex = 0;
  loading = false;
  errorMessage = '';
  filters: EntryListFilters = EMPTY_ENTRY_FILTERS;
  rangeInvalid = false;
  accounts: Account[] = [];
  methods: PaymentMethod[] = [];

  readonly filterForm = inject(FormBuilder).nonNullable.group({
    dateFrom: '',
    dateTo: '',
    accountId: '',
    method: '',
    origin: '' as EntryOrigin | '',
  });

  private api = inject(EntriesApiService);
  private accountingApi = inject(AccountingApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  get filtersActive(): boolean {
    return hasActiveFilters(this.filters);
  }

  get emptyWithFilters(): boolean {
    return !this.loading && !this.errorMessage && this.rows.length === 0 && this.filtersActive;
  }

  get emptyBook(): boolean {
    return !this.loading && !this.errorMessage && this.rows.length === 0 && !this.filtersActive;
  }

  /** Filtros aplicados en texto, para el vacío con filtros. */
  get appliedFilters(): string[] {
    const f = this.filters;
    const applied: string[] = [];
    if (f.dateFrom) applied.push(`${tr('COMMON.DESDE')}: ${f.dateFrom}`);
    if (f.dateTo) applied.push(`${tr('COMMON.HASTA')}: ${f.dateTo}`);
    if (f.accountId) applied.push(`${tr('ACCOUNTING.ENTRIES.CUENTA')}: ${this.accountName(f.accountId)}`);
    if (f.method) applied.push(`${tr('COMMON.METODO')}: ${this.methodName(f.method)}`);
    if (f.origin) applied.push(`${tr('COMMON.ORIGEN')}: ${originLabel(f.origin)}`);
    return applied;
  }

  get messages(): { emptyMessage: string; totalMessage: string } {
    return { emptyMessage: '', totalMessage: tr('COMMON.IN_TOTAL') };
  }

  ngOnInit(): void {
    this.accountingApi.listAccounts().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (accounts) => (this.accounts = accounts),
      error: () => undefined, // el filtro de cuenta queda vacío; el listado sigue funcionando
    });
    this.accountingApi.listMethods().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (methods) => (this.methods = methods),
      error: () => undefined,
    });

    this.reload$
      .pipe(
        switchMap(() => {
          this.loading = true;
          this.errorMessage = '';
          return this.api.list({ ...this.filters, page: this.pageIndex + 1, pageSize: this.pageSize }).pipe(
            catchError((err: AccountingApiError) => {
              this.errorMessage = err.message;
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
        this.totals = page.totals;
        this.coverage = page.coverage;
      });

    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      this.filters = filtersFromParams(params);
      this.pageIndex = 0;
      this.rangeInvalid = false;
      this.filterForm.setValue(this.filters, { emitEvent: false });
      this.reload$.next();
    });

    this.filterForm.valueChanges
      .pipe(debounceTime(FILTER_DEBOUNCE_MS), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.applyForm());
  }

  /** Pasa lo escrito en el formulario a la URL (que dispara la consulta). Un rango invertido no consulta. */
  applyForm(): void {
    const next: EntryListFilters = this.filterForm.getRawValue();
    this.rangeInvalid = isRangeInvalid(next);
    if (this.rangeInvalid) {
      return;
    }
    void this.router.navigate([LIST_PATH], { queryParams: filtersToQuery(next) });
  }

  clearFilters(): void {
    void this.router.navigate([LIST_PATH]);
  }

  retry(): void {
    this.reload$.next();
  }

  onPage(event: { offset: number }): void {
    // ngx-datatable también emite `page` al inicializarse; sin cambio de página no se vuelve a pedir.
    if (event.offset === this.pageIndex) {
      return;
    }
    this.pageIndex = event.offset;
    this.reload$.next();
  }

  originLabel(origin: EntryOrigin): string {
    return originLabel(origin);
  }

  originClass(origin: EntryOrigin): string {
    return ORIGIN_CLASSES[origin];
  }

  amount(amount: string, currency: string): string {
    return formatAmount(amount, currency);
  }

  document(entry: Entry): string {
    return documentLabel(entry);
  }

  link(entry: Entry): string[] | null {
    return sourceLink(entry);
  }

  private accountName(id: string): string {
    return this.accounts.find((a) => a.id === id)?.name ?? id;
  }

  private methodName(code: string): string {
    return this.methods.find((m) => m.code === code)?.label ?? code;
  }
}
