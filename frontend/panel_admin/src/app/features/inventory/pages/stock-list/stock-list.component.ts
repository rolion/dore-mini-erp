import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { EMPTY, Subject, catchError, finalize, switchMap, tap } from 'rxjs';
import { InventoryApiError } from '../../models/api-error';
import { StockBalance, formatQuantity } from '../../models/stock';
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
  readonly warehouseControl = new FormControl<string>(ALL_WAREHOUSES, { nonNullable: true });

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
              warehouseId: this.warehouseControl.value || undefined,
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

    // Almacenes activos para el filtro; si viene `warehouse_id` (tras una apertura) se conserva, si no, «Todos».
    const requested = this.route.snapshot.queryParamMap.get('warehouse_id');
    this.warehousesApi
      .list({ active: true, pageSize: 100 })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (page) => {
          this.warehouses = page.results;
          const known = page.results.some((warehouse) => warehouse.id === requested);
          this.warehouseControl.setValue(requested && known ? requested : ALL_WAREHOUSES, { emitEvent: false });
          this.reload();
        },
        error: () => this.reload(),
      });
    this.warehouseControl.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.page = 1;
      this.reload();
    });
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

  openMovements(row: StockBalance): void {
    this.router.navigate(['/pocketbiz/inventory/movements'], {
      queryParams: { warehouse_id: row.warehouseId, product_id: row.productId },
    });
  }

  display(quantity: string): string {
    return formatQuantity(quantity);
  }
}
