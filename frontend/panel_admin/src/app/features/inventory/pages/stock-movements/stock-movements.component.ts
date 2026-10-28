import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { InventoryApiError } from '../../models/api-error';
import { MOVEMENT_TYPE_LABELS, MovementsSummary, StockMovement, formatQuantity } from '../../models/stock';
import { StockApiService } from '../../services/stock-api.service';

/** Movimientos de un producto en un almacén (se abre desde Existencias). */
@Component({
  selector: 'app-stock-movements',
  templateUrl: './stock-movements.component.html',
  styleUrl: './stock-movements.component.scss',
  imports: [RouterLink, DatePipe, NgbPagination],
})
export class StockMovementsComponent implements OnInit {
  readonly pageSize = 20;

  summary: MovementsSummary | null = null;
  rows: StockMovement[] = [];
  count = 0;
  page = 1;
  loading = true;
  errorMessage = '';

  private stockApi = inject(StockApiService);
  private route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);
  private warehouseId: string | null = null;
  private productId: string | null = null;

  ngOnInit(): void {
    const params = this.route.snapshot.queryParamMap;
    this.warehouseId = params.get('warehouse_id');
    this.productId = params.get('product_id');
    this.load();
  }

  load(): void {
    if (!this.warehouseId || !this.productId) {
      this.loading = false;
      this.errorMessage = 'Falta el producto o el almacén. Vuelve a Existencias y elige un producto.';
      return;
    }
    this.loading = true;
    this.errorMessage = '';
    this.stockApi
      .movements(this.warehouseId, this.productId, this.page, this.pageSize)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (page) => {
          this.summary = page.summary;
          this.rows = page.results;
          this.count = page.count;
          this.loading = false;
        },
        error: (err: InventoryApiError) => {
          this.loading = false;
          this.errorMessage = err.message;
        },
      });
  }

  goTo(page: number): void {
    this.page = page;
    this.load();
  }

  typeLabel(type: string): string {
    return MOVEMENT_TYPE_LABELS[type] ?? type;
  }

  display(quantity: string): string {
    return formatQuantity(quantity);
  }

  get backLink(): { path: string[]; params: Record<string, string> } {
    const warehouseId = this.warehouseId ?? '';
    return { path: ['/pocketbiz/inventory/stock'], params: warehouseId ? { warehouse_id: warehouseId } : {} };
  }
}
