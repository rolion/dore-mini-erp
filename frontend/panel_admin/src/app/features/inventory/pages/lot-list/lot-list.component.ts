import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { EMPTY, Subject, catchError, debounceTime, finalize, switchMap } from 'rxjs';
import { InventoryApiError } from '../../models/api-error';
import { LOT_STATUS_LABELS, LotListParams, LotStatus, LotStatusFilter, StockLot } from '../../models/lot';
import { formatQuantity } from '../../models/stock';
import { Warehouse } from '../../models/warehouse';
import { LotsApiService } from '../../services/lots-api.service';
import { WarehousesApiService } from '../../services/warehouses-api.service';

/** Inventario › Lotes: consulta de solo lectura del saldo físico y del disponible para empaque de cada lote. */
@Component({
  selector: 'app-lot-list',
  templateUrl: './lot-list.component.html',
  styleUrl: './lot-list.component.scss',
  imports: [TranslatePipe, RouterLink, ReactiveFormsModule, DatePipe, NgbPagination],
})
export class LotListComponent implements OnInit {
  readonly pageSize = 10;
  readonly filterForm = inject(FormBuilder).nonNullable.group({
    search: [''],
    warehouseId: [''],
    status: ['' as LotStatusFilter],
    withStock: [false],
  });

  rows: StockLot[] = [];
  total = 0;
  /** Página actual base 1 (`ngb-pagination`). */
  page = 1;
  loading = false;
  errorMessage = '';
  warehouses: Warehouse[] = [];

  private api = inject(LotsApiService);
  private warehousesApi = inject(WarehousesApiService);
  private route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  get filtersActive(): boolean {
    const f = this.filterForm.getRawValue();
    return !!(f.search || f.warehouseId || f.status || f.withStock);
  }

  ngOnInit(): void {
    // Los enlaces desde otras pantallas pueden traer el producto (?product_id=) para ver sus lotes.
    this.productId = this.route.snapshot.queryParamMap.get('product_id') ?? '';
    this.reload$
      .pipe(
        switchMap(() => {
          this.loading = true;
          this.errorMessage = '';
          return this.api.list(this.params()).pipe(
            catchError((err: InventoryApiError) => {
              this.errorMessage = err.message;
              return EMPTY;
            }),
            finalize(() => (this.loading = false)),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((result) => {
        this.rows = result.results;
        this.total = result.count;
      });
    this.warehousesApi
      .list({ pageSize: 100 })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: (result) => (this.warehouses = result.results), error: () => (this.warehouses = []) });
    this.filterForm.valueChanges
      .pipe(debounceTime(250), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.page = 1;
        this.reload$.next();
      });
    this.reload$.next();
  }

  /** Producto por el que se filtra si llegó por enlace; vacío = todos. */
  productId = '';

  statusLabel(status: LotStatus): string {
    return LOT_STATUS_LABELS[status];
  }

  display(quantity: string): string {
    return formatQuantity(quantity);
  }

  stockLink(row: StockLot): string[] {
    return ['/pocketbiz/inventory/stock', row.productId, row.warehouseId];
  }

  reload(): void {
    this.reload$.next();
  }

  clearFilters(): void {
    this.productId = '';
    this.filterForm.setValue({ search: '', warehouseId: '', status: '', withStock: false });
  }

  onPage(page: number): void {
    if (page === this.page) return;
    this.page = page;
    this.reload$.next();
  }

  private params(): LotListParams {
    const { search, warehouseId, status, withStock } = this.filterForm.getRawValue();
    return {
      search: search.trim() || undefined,
      productId: this.productId || undefined,
      warehouseId: warehouseId || undefined,
      status: status || undefined,
      withStock: withStock || undefined,
      page: this.page,
      pageSize: this.pageSize,
    };
  }
}
