import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
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
  SALES_ORDER_SOURCE,
  SOURCE_ROUTES,
  SOURCE_TYPE_OPTIONS,
  StockMovement,
  movementTypeLabel,
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
  private route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  /** Pedido de venta cuyas salidas se están viendo (llega desde el detalle del pedido); vacío = sin filtrar. */
  sourceId = '';

  get filtersActive(): boolean {
    return !!this.sourceId || Object.values(this.filterForm.getRawValue()).some((value) => value !== '');
  }

  /** Código visible del pedido filtrado, tomado de los movimientos cargados. */
  get orderFilterLabel(): string {
    return this.rows.find((row) => row.reference)?.reference || 'seleccionado';
  }

  ngOnInit(): void {
    // Existencias enlaza aquí con ?product_id=&warehouse_id= para ver los movimientos de una fila.
    const query = this.route.snapshot.queryParamMap;
    const fromOrder = query.get('source_type') === SALES_ORDER_SOURCE && !!query.get('source_id');
    this.sourceId = fromOrder ? (query.get('source_id') ?? '') : '';
    this.filterForm.patchValue(
      {
        productId: query.get('product_id') ?? '',
        warehouseId: query.get('warehouse_id') ?? '',
        sourceType: fromOrder ? SALES_ORDER_SOURCE : '',
      },
      { emitEvent: false },
    );
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
      .subscribe({ next: (page) => this.setProducts(page.results), error: () => this.setProducts([]) });
    this.warehousesApi
      .list({ pageSize: 100 })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: (page) => (this.warehouses = page.results), error: () => (this.warehouses = []) });

    this.filterForm.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      if (this.sourceId && this.filterForm.getRawValue().sourceType !== SALES_ORDER_SOURCE) {
        this.sourceId = ''; // cambiar la clase de origen deja de filtrar por ese pedido
      }
      this.pageIndex = 0;
      if (this.validateRange()) {
        this.reload$.next();
      }
    });
    this.reload$.next();
  }

  /** El producto del filtro (p. ej. el que llega desde Existencias, activo o no) siempre debe poder elegirse. */
  private setProducts(products: Product[]): void {
    this.products = products;
    const selected = this.filterForm.getRawValue().productId;
    if (selected && !products.some((product) => product.id === selected)) {
      this.productsApi
        .get(selected)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({ next: (product) => (this.products = [...this.products, product]), error: () => undefined });
    }
  }

  kindLabel(kind: MovementKind): string {
    return MOVEMENT_KIND_LABELS[kind];
  }

  typeLabel(movement: StockMovement): string {
    return movementTypeLabel(movement);
  }

  /** Quita el filtro por pedido y vuelve a cargar (los demás filtros se conservan). */
  clearOrderFilter(): void {
    this.sourceId = '';
    this.filterForm.patchValue({ sourceType: '' });
  }

  statusLabel(status: MovementStatus): string {
    return MOVEMENT_STATUS_LABELS[status];
  }

  reload(): void {
    this.reload$.next();
  }

  clearFilters(): void {
    this.sourceId = '';
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
      sourceId: sourceType && this.sourceId ? this.sourceId : undefined,
      page: this.pageIndex + 1,
      pageSize: this.pageSize,
    };
  }
}
