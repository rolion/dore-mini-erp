import { DatePipe, NgTemplateOutlet } from '@angular/common';
import { Component, DestroyRef, ElementRef, OnInit, inject, viewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Params, Router, RouterLink } from '@angular/router';
import { NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { EMPTY, Subject, catchError, debounceTime, finalize, switchMap } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { CompactViewportService } from '../../../../core/layout/compact-viewport.service';
import { Account, AccountingApiError } from '../../models/accounting';
import {
  EMPTY_JOURNAL_FILTERS,
  JOURNAL_SOURCES,
  JournalFilters,
  JournalRow,
  JournalSource,
  SOURCE_CLASSES,
  hasActiveFilters,
  isRangeInvalid,
  sourceLabel,
} from '../../models/journal';
import { AccountingApiService } from '../../services/accounting-api.service';
import { JournalApiService } from '../../services/journal-api.service';
import { JournalFiltersState } from '../../services/journal-filters-state';

const LIST_PATH = '/pocketbiz/accounting/journal';
const FILTER_DEBOUNCE_MS = 300;

export function journalFiltersFromParams(params: { get(name: string): string | null }): JournalFilters {
  const source = params.get('source');
  return {
    dateFrom: params.get('date_from') ?? '',
    dateTo: params.get('date_to') ?? '',
    accountId: params.get('account_id') ?? '',
    source: JOURNAL_SOURCES.includes(source as JournalSource) ? (source as JournalSource) : '',
  };
}

export function journalFiltersToQuery(filters: JournalFilters, page = 0): Params {
  const query: Params = {};
  if (filters.dateFrom) query['date_from'] = filters.dateFrom;
  if (filters.dateTo) query['date_to'] = filters.dateTo;
  if (filters.accountId) query['account_id'] = filters.accountId;
  if (filters.source) query['source'] = filters.source;
  if (page > 0) query['page'] = page + 1;
  return query;
}

/** Contabilidad › Movimientos: asientos de solo lectura, filtros y página en la URL (orden estable del servidor). */
@Component({
  selector: 'app-journal-list',
  templateUrl: './journal-list.component.html',
  imports: [TranslatePipe, RouterLink, ReactiveFormsModule, NgxDatatableModule, DatePipe, NgbPagination, NgTemplateOutlet],
  styleUrl: './journal-list.component.scss',
})
export class JournalListComponent implements OnInit {
  readonly pageSize = 20;
  readonly sources = JOURNAL_SOURCES;
  rows: JournalRow[] = [];
  total = 0;
  /** Página actual base 0, como espera ngx-datatable. */
  pageIndex = 0;
  loading = false;
  errorMessage = '';
  filters: JournalFilters = EMPTY_JOURNAL_FILTERS;
  rangeInvalid = false;
  accounts: Account[] = [];
  /** Solo en pantalla estrecha: el panel de filtros se muestra al pulsar «Filtros» y se cierra al aplicar. */
  filtersOpen = false;
  readonly compact = inject(CompactViewportService).compact;
  private readonly summary = viewChild<ElementRef<HTMLElement>>('summary');

  readonly filterForm = inject(FormBuilder).nonNullable.group({
    dateFrom: '',
    dateTo: '',
    accountId: '',
    source: '' as JournalSource | '',
  });

  private api = inject(JournalApiService);
  private accountingApi = inject(AccountingApiService);
  private state = inject(JournalFiltersState);
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

  get activeFilterCount(): number {
    return this.appliedFilters.length;
  }

  /** Rango visible para «Mostrando 1–20 de N». */
  get shownFrom(): number {
    return this.rows.length === 0 ? 0 : this.pageIndex * this.pageSize + 1;
  }

  get shownTo(): number {
    return this.pageIndex * this.pageSize + this.rows.length;
  }

  get appliedFilters(): string[] {
    const f = this.filters;
    const applied: string[] = [];
    if (f.dateFrom) applied.push(`${tr('COMMON.DESDE')}: ${f.dateFrom}`);
    if (f.dateTo) applied.push(`${tr('COMMON.HASTA')}: ${f.dateTo}`);
    if (f.accountId) applied.push(`${tr('ACCOUNTING.ENTRIES.CUENTA')}: ${this.accountName(f.accountId)}`);
    if (f.source) applied.push(`${tr('COMMON.ORIGEN')}: ${sourceLabel(f.source)}`);
    return applied;
  }

  get messages(): { emptyMessage: string; totalMessage: string } {
    return { emptyMessage: '', totalMessage: tr('COMMON.IN_TOTAL') };
  }

  ngOnInit(): void {
    this.accountingApi.listAccounts().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (accounts) => (this.accounts = accounts),
      error: () => undefined, // el filtro de cuenta queda vacío; la lista sigue funcionando
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
      });

    this.restoreRememberedFilters();
    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      this.filters = journalFiltersFromParams(params);
      const page = Number(params.get('page'));
      this.pageIndex = Number.isInteger(page) && page > 1 ? page - 1 : 0;
      this.rangeInvalid = false;
      this.filterForm.setValue(this.filters, { emitEvent: false });
      this.state.remember(this.filters, this.pageIndex);
      this.reload$.next();
    });

    this.filterForm.valueChanges
      .pipe(debounceTime(FILTER_DEBOUNCE_MS), takeUntilDestroyed(this.destroyRef))
      // En pantalla estrecha se aplica con el botón «Aplicar»: cerrar el panel al elegir «Desde» impediría elegir «Hasta».
      .subscribe(() => {
        if (!this.compact()) this.applyForm();
      });
  }

  /** Al volver desde un detalle sin parámetros en la URL, recupera los filtros y la página guardados. */
  private restoreRememberedFilters(): void {
    if (this.route.snapshot.queryParamMap.keys.length > 0) return;
    const remembered = this.state.filters;
    if (hasActiveFilters(remembered) || this.state.pageIndex > 0) {
      void this.router.navigate([LIST_PATH], { queryParams: journalFiltersToQuery(remembered, this.state.pageIndex), replaceUrl: true });
    }
  }

  applyForm(): void {
    const next: JournalFilters = this.filterForm.getRawValue();
    this.rangeInvalid = isRangeInvalid(next);
    if (this.rangeInvalid) return;
    void this.router.navigate([LIST_PATH], { queryParams: journalFiltersToQuery(next) });
  }

  /** «Aplicar» en pantalla estrecha: aplica, cierra el panel y lleva el foco al resumen de resultados. */
  applyAndClose(): void {
    this.applyForm();
    if (this.rangeInvalid) return;
    this.filtersOpen = false;
    queueMicrotask(() => this.summary()?.nativeElement.focus());
  }

  clearFilters(): void {
    this.filtersOpen = false;
    void this.router.navigate([LIST_PATH]);
  }

  retry(): void {
    this.reload$.next();
  }

  onPage(event: { offset: number }): void {
    // ngx-datatable también emite `page` al inicializarse; sin cambio de página no se vuelve a pedir.
    if (event.offset === this.pageIndex) return;
    void this.router.navigate([LIST_PATH], { queryParams: journalFiltersToQuery(this.filters, event.offset) });
  }

  /** Paginación de las tarjetas (`ngb-pagination` es base 1) y vuelta al inicio de la lista. */
  onPageNumber(page: number): void {
    this.onPage({ offset: page - 1 });
    queueMicrotask(() => {
      const el = this.summary()?.nativeElement;
      el?.scrollIntoView({ block: 'start' });
      el?.focus();
    });
  }

  sourceLabel(source: JournalSource): string {
    return sourceLabel(source);
  }

  sourceClass(source: JournalSource): string {
    return SOURCE_CLASSES[source];
  }

  private accountName(id: string): string {
    return this.accounts.find((a) => a.id === id)?.name ?? id;
  }
}
