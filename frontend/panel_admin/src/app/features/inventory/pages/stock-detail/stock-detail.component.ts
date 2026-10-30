import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { EMPTY, Subject, catchError, finalize, switchMap, tap } from 'rxjs';
import { categoryLabel } from '../../../products/models/product';
import { InventoryApiError } from '../../models/api-error';
import {
  MOVEMENT_KIND_LABELS,
  MOVEMENT_STATUS_LABELS,
  MovementKind,
  MovementStatus,
  SOURCE_ROUTES,
  StockMovement,
} from '../../models/movement';
import { StockPosition, formatQuantity } from '../../models/stock';
import { MovementsApiService } from '../../services/movements-api.service';
import { StockApiService } from '../../services/stock-api.service';

/** Inventario › Existencias › detalle de un producto en un almacén, con su historial de movimientos. */
@Component({
  selector: 'app-stock-detail',
  templateUrl: './stock-detail.component.html',
  styleUrl: './stock-detail.component.scss',
  imports: [RouterLink, NgbPagination, DatePipe],
})
export class StockDetailComponent implements OnInit {
  readonly pageSize = 10;

  position: StockPosition | null = null;
  loading = true;
  notFound = false;
  errorMessage = '';

  movements: StockMovement[] = [];
  movementsCount = 0;
  movementsPage = 1;
  movementsLoading = false;
  movementsError = '';

  private stockApi = inject(StockApiService);
  private movementsApi = inject(MovementsApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private loadMovements$ = new Subject<void>();

  ngOnInit(): void {
    this.loadMovements$
      .pipe(
        tap(() => {
          this.movementsLoading = true;
          this.movementsError = '';
        }),
        switchMap(() =>
          this.movementsApi
            .list({
              productId: this.position?.productId,
              warehouseId: this.position?.warehouseId,
              page: this.movementsPage,
              pageSize: this.pageSize,
            })
            .pipe(
              catchError((err: InventoryApiError) => {
                this.movementsError = err.message;
                return EMPTY;
              }),
              finalize(() => (this.movementsLoading = false)),
            ),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((page) => {
        this.movements = page.results;
        this.movementsCount = page.count;
      });
    this.load();
  }

  load(): void {
    const params = this.route.snapshot.paramMap;
    const productId = params.get('productId') ?? '';
    const warehouseId = params.get('warehouseId') ?? '';
    this.loading = true;
    this.errorMessage = '';
    this.notFound = false;
    this.stockApi
      .get(productId, warehouseId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (position) => {
          this.position = position;
          this.loading = false;
          this.reloadMovements();
        },
        error: (err: InventoryApiError) => {
          this.loading = false;
          this.notFound = err.status === 404;
          this.errorMessage = this.notFound ? '' : err.message;
        },
      });
  }

  reloadMovements(): void {
    this.loadMovements$.next();
  }

  goTo(page: number): void {
    this.movementsPage = page;
    this.reloadMovements();
  }

  display(quantity: string): string {
    return formatQuantity(quantity);
  }

  kindLabel(kind: MovementKind): string {
    return MOVEMENT_KIND_LABELS[kind];
  }

  statusLabel(status: MovementStatus): string {
    return MOVEMENT_STATUS_LABELS[status];
  }

  sourceLink(movement: StockMovement): string[] | null {
    const source = movement.source;
    const route = source ? SOURCE_ROUTES[source.type] : undefined;
    return source && source.available && route ? route(source.id) : null;
  }

  openMovements(): void {
    if (this.position) {
      this.router.navigate(['/pocketbiz/inventory/movements'], {
        queryParams: { warehouse_id: this.position.warehouseId, product_id: this.position.productId },
      });
    }
  }

  /** Por qué no se ofrece «Registrar apertura» (solo cuando el par ya tiene detalle y no cumple condiciones). */
  get openingNote(): string {
    const position = this.position;
    if (!position || position.canRegisterOpening) {
      return '';
    }
    if (position.hasHistory) {
      return 'La apertura solo procede sin movimientos previos; las correcciones se hacen con un ajuste.';
    }
    return 'Producto o almacén inactivo.';
  }

  /** Por qué no se ofrece «Registrar ajuste» (solo cuando el almacén está inactivo). */
  get adjustmentNote(): string {
    return this.position && !this.position.canRegisterAdjustment ? 'Almacén inactivo: no se pueden registrar ajustes.' : '';
  }

  /** Contexto con el que los flujos de apertura y ajuste preseleccionan el par y vuelven a este detalle. */
  get operationParams(): Record<string, string> {
    return {
      warehouse_id: this.position?.warehouseId ?? '',
      product_id: this.position?.productId ?? '',
      return: 'stock',
    };
  }

  get categoryText(): string {
    return categoryLabel(this.position?.category ?? null);
  }
}
