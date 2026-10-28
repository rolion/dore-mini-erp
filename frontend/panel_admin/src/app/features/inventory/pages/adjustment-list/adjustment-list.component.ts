import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { EMPTY, Subject, catchError, finalize, switchMap, tap } from 'rxjs';
import { Product } from '../../../products/models/product';
import { ProductsApiService } from '../../../products/services/products-api.service';
import { AdjustmentListParams, StockAdjustment, signedDifference } from '../../models/adjustment';
import { InventoryApiError } from '../../models/api-error';
import { MOVEMENT_STATUS_LABELS, MovementStatus } from '../../models/movement';
import { formatQuantity } from '../../models/stock';
import { Warehouse } from '../../models/warehouse';
import { AdjustmentsApiService } from '../../services/adjustments-api.service';
import { WarehousesApiService } from '../../services/warehouses-api.service';

export const INVALID_RANGE_MESSAGE = 'La fecha final no puede ser anterior a la inicial.';

/** Inventario › Ajustes de existencias: lista de ajustes confirmados con filtros y punto de entrada de «Nuevo ajuste». */
@Component({
  selector: 'app-adjustment-list',
  templateUrl: './adjustment-list.component.html',
  styleUrl: './adjustment-list.component.scss',
  imports: [RouterLink, ReactiveFormsModule, DatePipe, NgbPagination],
})
export class AdjustmentListComponent implements OnInit {
  readonly pageSize = 25;
  readonly filterForm = inject(FormBuilder).nonNullable.group({
    dateFrom: [''],
    dateTo: [''],
    productId: [''],
    warehouseId: [''],
  });

  rows: StockAdjustment[] = [];
  count = 0;
  page = 1;
  loading = false;
  errorMessage = '';
  rangeError = '';
  products: Product[] = [];
  warehouses: Warehouse[] = [];

  private api = inject(AdjustmentsApiService);
  private productsApi = inject(ProductsApiService);
  private warehousesApi = inject(WarehousesApiService);
  private destroyRef = inject(DestroyRef);
  private load$ = new Subject<void>();

  get filtersActive(): boolean {
    return Object.values(this.filterForm.getRawValue()).some((value) => value !== '');
  }

  ngOnInit(): void {
    this.load$
      .pipe(
        tap(() => {
          this.loading = true;
          this.errorMessage = '';
        }),
        switchMap(() =>
          this.api.list(this.params()).pipe(
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

    this.productsApi
      .list({ pageSize: 100 })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: (page) => (this.products = page.results), error: () => (this.products = []) });
    this.warehousesApi
      .list({ pageSize: 100 })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: (page) => (this.warehouses = page.results), error: () => (this.warehouses = []) });

    this.filterForm.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.page = 1;
      if (this.validateRange()) {
        this.reload();
      }
    });
    this.reload();
  }

  reload(): void {
    this.load$.next();
  }

  goTo(page: number): void {
    this.page = page;
    this.reload();
  }

  clearFilters(): void {
    this.filterForm.setValue({ dateFrom: '', dateTo: '', productId: '', warehouseId: '' });
  }

  statusLabel(status: MovementStatus): string {
    return MOVEMENT_STATUS_LABELS[status];
  }

  display(quantity: string): string {
    return formatQuantity(quantity);
  }

  signed(difference: string): string {
    return signedDifference(difference);
  }

  private validateRange(): boolean {
    const { dateFrom, dateTo } = this.filterForm.getRawValue();
    this.rangeError = dateFrom && dateTo && dateFrom > dateTo ? INVALID_RANGE_MESSAGE : '';
    return !this.rangeError;
  }

  private params(): AdjustmentListParams {
    const { dateFrom, dateTo, productId, warehouseId } = this.filterForm.getRawValue();
    return {
      dateFrom: dateFrom || undefined,
      dateTo: dateTo || undefined,
      productId: productId || undefined,
      warehouseId: warehouseId || undefined,
      page: this.page,
      pageSize: this.pageSize,
    };
  }
}
