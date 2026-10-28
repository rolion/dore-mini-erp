import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { EMPTY, Subject, catchError, debounceTime, finalize, switchMap, tap } from 'rxjs';
import { InventoryApiError } from '../../models/api-error';
import {
  ACTIVE_FILTER_OPTIONS,
  ActiveFilter,
  BALANCE_FILTER_OPTIONS,
  BalanceFilter,
  StockBalance,
  formatQuantity,
} from '../../models/stock';
import { Warehouse } from '../../models/warehouse';
import { StockApiService } from '../../services/stock-api.service';
import { WarehousesApiService } from '../../services/warehouses-api.service';

export const ALL_WAREHOUSES = '';

/** Inventario › Existencias: saldos por almacén y punto de entrada de «Registrar apertura». */
@Component({
  selector: 'app-stock-list',
  templateUrl: './stock-list.component.html',
  styleUrl: './stock-list.component.scss',
  imports: [ReactiveFormsModule, RouterLink, NgbPagination],
})
export class StockListComponent implements OnInit {
  readonly pageSize = 20;
  readonly activeOptions = ACTIVE_FILTER_OPTIONS;
  readonly balanceOptions = BALANCE_FILTER_OPTIONS;
  readonly filterForm = inject(FormBuilder).nonNullable.group({
    search: [''],
    warehouseId: [ALL_WAREHOUSES],
    active: ['true' as ActiveFilter],
    balance: ['' as BalanceFilter],
  });

  warehouses: Warehouse[] = [];
  rows: StockBalance[] = [];
  count = 0;
  page = 1;
  loading = false;
  errorMessage = '';

  private stockApi = inject(StockApiService);
  private warehousesApi = inject(WarehousesApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private load$ = new Subject<void>();

  ngOnInit(): void {
    this.load$
      .pipe(
        tap(() => {
          this.loading = true;
          this.errorMessage = '';
        }),
        switchMap(() =>
          this.stockApi
            .list({
              search: this.filterForm.controls.search.value.trim() || undefined,
              warehouseId: this.filterForm.controls.warehouseId.value || undefined,
              active: this.filterForm.controls.active.value,
              balance: this.filterForm.controls.balance.value || undefined,
              page: this.page,
              pageSize: this.pageSize,
            })
            .pipe(
              catchError((err: InventoryApiError) => {
                this.errorMessage = err.message;
                this.rows = [];
                this.count = 0;
                return EMPTY;
              }),
              finalize(() => (this.loading = false)),
            ),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((page) => {
        this.rows = page.results;
        this.count = page.count;
      });

    // Almacenes para el filtro (también los inactivos); si viene `warehouse_id` (tras una apertura) se conserva.
    const requested = this.route.snapshot.queryParamMap.get('warehouse_id');
    this.warehousesApi
      .list({ pageSize: 100 })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (page) => {
          this.warehouses = page.results;
          const known = page.results.some((warehouse) => warehouse.id === requested);
          this.filterForm.controls.warehouseId.setValue(requested && known ? requested : ALL_WAREHOUSES, {
            emitEvent: false,
          });
          this.reload();
        },
        error: () => this.reload(),
      });
    this.filterForm.valueChanges.pipe(debounceTime(250), takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.page = 1;
      this.reload();
    });
  }

  get filtersActive(): boolean {
    const { search, warehouseId, active, balance } = this.filterForm.getRawValue();
    return search !== '' || warehouseId !== ALL_WAREHOUSES || active !== 'true' || balance !== '';
  }

  clearFilters(): void {
    this.filterForm.setValue({ search: '', warehouseId: ALL_WAREHOUSES, active: 'true', balance: '' });
  }

  reload(): void {
    this.load$.next();
  }

  goTo(page: number): void {
    this.page = page;
    this.reload();
  }

  openingLink(): string[] {
    return ['/pocketbiz/inventory/stock/opening'];
  }

  detailLink(row: StockBalance): string[] {
    return ['/pocketbiz/inventory/stock', row.productId, row.warehouseId];
  }

  openMovements(row: StockBalance): void {
    this.router.navigate(['/pocketbiz/inventory/movements'], {
      queryParams: { warehouse_id: row.warehouseId, product_id: row.productId },
    });
  }

  display(quantity: string): string {
    return formatQuantity(quantity);
  }
}
