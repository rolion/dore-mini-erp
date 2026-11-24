import { BreakpointObserver } from '@angular/cdk/layout';
import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgbCollapse, NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { Subject, catchError, debounceTime, distinctUntilChanged, finalize, of, switchMap, tap } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { Warehouse, WarehousesApiService } from '../../../inventory';
import { CrmCustomer, CrmListMeta } from '../../models/crm-customer';
import { CrmCustomersApiService } from '../../services/crm-customers-api.service';

/** Por debajo de `lg` (992 px) los filtros son un panel colapsable con «Aplicar» y las filas son tarjetas. */
export const COMPACT_QUERY = '(max-width: 991.98px)';

@Component({
  selector: 'app-crm-customer-list',
  templateUrl: './crm-customer-list.component.html',
  styleUrl: './crm-customer-list.component.scss',
  imports: [TranslatePipe, RouterLink, NgxDatatableModule, ReactiveFormsModule, NgbCollapse, NgbPagination, MoneyPipe, DatePipe],
})
export class CrmCustomerListComponent implements OnInit {
  readonly pageSize = 10;
  readonly searchControl = new FormControl('', { nonNullable: true });
  readonly warehouseControl = new FormControl('', { nonNullable: true });

  rows: CrmCustomer[] = [];
  total = 0;
  /** Página actual base 0, como espera ngx-datatable. */
  pageIndex = 0;
  loading = false;
  failed = false;
  compact = false;
  filtersCollapsed = true;
  meta: CrmListMeta = { sales_enabled: true, warehouse_filter_enabled: false };
  warehouses: Warehouse[] = [];

  protected applied = { search: '', warehouseId: '' };
  private warehousesLoaded = false;

  private breakpoints = inject(BreakpointObserver);
  private api = inject(CrmCustomersApiService);
  private warehousesApi = inject(WarehousesApiService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  get messages() {
    return { emptyMessage: '', totalMessage: tr('COMMON.IN_TOTAL') };
  }

  /** Sin resultados y sin filtros: la empresa aún no tiene clientes. */
  get hasFilters(): boolean {
    return !!(this.applied.search || this.applied.warehouseId);
  }

  get activeFilterCount(): number {
    return (this.searchControl.value.trim() ? 1 : 0) + (this.warehouseControl.value ? 1 : 0);
  }

  get warehouseName(): string {
    return this.warehouses.find((w) => w.id === this.applied.warehouseId)?.name ?? '';
  }

  get rangeStart(): number {
    return this.total === 0 ? 0 : this.pageIndex * this.pageSize + 1;
  }

  get rangeEnd(): number {
    return Math.min((this.pageIndex + 1) * this.pageSize, this.total);
  }

  ngOnInit(): void {
    const query = this.route.snapshot.queryParamMap;
    this.searchControl.setValue(query.get('search') ?? '', { emitEvent: false });
    this.warehouseControl.setValue(query.get('warehouse_id') ?? '', { emitEvent: false });
    this.pageIndex = Math.max(0, (Number(query.get('page')) || 1) - 1);
    this.applied = { search: this.searchControl.value.trim(), warehouseId: this.warehouseControl.value };

    this.reload$
      .pipe(
        switchMap(() => {
          this.loading = true;
          this.failed = false;
          return this.api
            .list({
              search: this.applied.search,
              warehouseId: this.applied.warehouseId,
              page: this.pageIndex + 1,
              pageSize: this.pageSize,
            })
            .pipe(
              tap(() => this.syncUrl()),
              catchError(() => {
                this.failed = true;
                return of(null);
              }),
              finalize(() => (this.loading = false)),
            );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((page) => {
        if (!page) return;
        this.rows = page.results;
        this.total = page.count;
        this.meta = page.meta;
        this.loadWarehousesOnce();
      });

    this.breakpoints
      .observe(COMPACT_QUERY)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => (this.compact = state.matches));

    // En pantalla estrecha los cambios se aplican con «Aplicar»; en escritorio, al instante.
    this.searchControl.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.applyIfWide());
    this.warehouseControl.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.applyIfWide());

    this.reload$.next();
  }

  toggleFilters(): void {
    this.filtersCollapsed = !this.filtersCollapsed;
  }

  applyFilters(): void {
    this.filtersCollapsed = true;
    this.syncAppliedAndReload();
  }

  clearFilters(): void {
    this.searchControl.setValue('', { emitEvent: false });
    this.warehouseControl.setValue('', { emitEvent: false });
    this.applyFilters();
  }

  retry(): void {
    this.reload$.next();
  }

  onCardsPage(page: number): void {
    this.onPage({ offset: page - 1 });
  }

  onPage(event: { offset: number }): void {
    // ngx-datatable también emite `page` al inicializarse; sin cambio de página no se vuelve a pedir.
    if (event.offset === this.pageIndex) return;
    this.pageIndex = event.offset;
    this.reload$.next();
  }

  private loadWarehousesOnce(): void {
    if (!this.meta.warehouse_filter_enabled || this.warehousesLoaded) return;
    this.warehousesLoaded = true;
    this.warehousesApi
      .list({ active: true, pageSize: 100 })
      .pipe(
        catchError(() => of(null)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((page) => (this.warehouses = page?.results ?? []));
  }

  private applyIfWide(): void {
    if (!this.compact) this.syncAppliedAndReload();
  }

  private syncAppliedAndReload(): void {
    this.applied = { search: this.searchControl.value.trim(), warehouseId: this.warehouseControl.value };
    this.pageIndex = 0;
    this.reload$.next();
  }

  /** Filtros y página viven en la URL para poder volver desde la ficha. */
  private syncUrl(): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      replaceUrl: true,
      queryParams: {
        search: this.applied.search || null,
        warehouse_id: this.applied.warehouseId || null,
        page: this.pageIndex > 0 ? this.pageIndex + 1 : null,
      },
    });
  }
}
