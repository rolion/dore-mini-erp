import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { EMPTY, Subject, catchError, finalize, switchMap } from 'rxjs';
import { Product } from '../../../products/models/product';
import { ProductsApiService } from '../../../products/services/products-api.service';
import { InventoryApiError } from '../../models/api-error';
import {
  MOVEMENT_KIND_LABELS,
  MOVEMENT_STATUS_LABELS,
  MovementKind,
  MovementListParams,
  MovementStatus,
  SOURCE_ROUTES,
  SOURCE_TYPE_OPTIONS,
  StockMovement,
} from '../../models/movement';
import { Warehouse } from '../../models/warehouse';
import { MovementsApiService } from '../../services/movements-api.service';
import { WarehousesApiService } from '../../services/warehouses-api.service';

export const INVALID_RANGE_MESSAGE = 'La fecha final no puede ser anterior a la inicial.';

@Component({
  selector: 'app-movement-list',
  templateUrl: './movement-list.component.html',
  styleUrl: './movement-list.component.scss',
  imports: [RouterLink, NgxDatatableModule, ReactiveFormsModule, DatePipe],
})
export class MovementListComponent implements OnInit {
  readonly pageSize = 10;
  readonly messages = { emptyMessage: 'Sin movimientos para los filtros elegidos.', totalMessage: 'en total' };
  readonly sourceOptions = SOURCE_TYPE_OPTIONS;
  readonly filterForm = inject(FormBuilder).nonNullable.group({
    dateFrom: [''],
    dateTo: [''],
    productId: [''],
    warehouseId: [''],
    kind: ['' as MovementKind | ''],
    sourceType: [''],
  });

  rows: StockMovement[] = [];
  total = 0;
  /** Página actual base 0, como espera ngx-datatable. */
  pageIndex = 0;
  loading = false;
  errorMessage = '';
  rangeError = '';
  products: Product[] = [];
  warehouses: Warehouse[] = [];

  private api = inject(MovementsApiService);
  private productsApi = inject(ProductsApiService);
  private warehousesApi = inject(WarehousesApiService);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  get filtersActive(): boolean {
    return Object.values(this.filterForm.getRawValue()).some((value) => value !== '');
  }

  ngOnInit(): void {
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
      .subscribe((page) => {
        this.rows = page.results;
        this.total = page.count;
      });

    this.productsApi
      .list({ pageSize: 100 })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: (page) => (this.products = page.results), error: () => (this.products = []) });
    this.warehousesApi
      .list({ pageSize: 100 })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: (page) => (this.warehouses = page.results), error: () => (this.warehouses = []) });

    this.filterForm.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.pageIndex = 0;
      if (this.validateRange()) {
        this.reload$.next();
      }
    });
    this.reload$.next();
  }

  kindLabel(kind: MovementKind): string {
    return MOVEMENT_KIND_LABELS[kind];
  }

  statusLabel(status: MovementStatus): string {
    return MOVEMENT_STATUS_LABELS[status];
  }

  reload(): void {
    this.reload$.next();
  }

  clearFilters(): void {
    this.filterForm.setValue({ dateFrom: '', dateTo: '', productId: '', warehouseId: '', kind: '', sourceType: '' });
  }

  onPage(event: { offset: number }): void {
    // ngx-datatable también emite `page` al inicializarse; sin cambio de página no se vuelve a pedir.
    if (event.offset === this.pageIndex) {
      return;
    }
    this.pageIndex = event.offset;
    this.reload$.next();
  }

  /** Enlace al documento de origen: solo con el módulo propietario habilitado y una pantalla de destino. */
  sourceLink(movement: StockMovement): string[] | null {
    const source = movement.source;
    const route = source ? SOURCE_ROUTES[source.type] : undefined;
    return source && source.available && route ? route(source.id) : null;
  }

  private validateRange(): boolean {
    const { dateFrom, dateTo } = this.filterForm.getRawValue();
    this.rangeError = dateFrom && dateTo && dateFrom > dateTo ? INVALID_RANGE_MESSAGE : '';
    return !this.rangeError;
  }

  private params(): MovementListParams {
    const { dateFrom, dateTo, productId, warehouseId, kind, sourceType } = this.filterForm.getRawValue();
    return {
      dateFrom: dateFrom || undefined,
      dateTo: dateTo || undefined,
      productId: productId || undefined,
      warehouseId: warehouseId || undefined,
      kind: kind || undefined,
      sourceType: sourceType || undefined,
      page: this.pageIndex + 1,
      pageSize: this.pageSize,
    };
  }
}
