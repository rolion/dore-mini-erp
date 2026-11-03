import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { EMPTY, Subject, catchError, finalize, switchMap } from 'rxjs';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { Product } from '../../../products/models/product';
import { ProductsApiService } from '../../../products/services/products-api.service';
import {
  COST_ORIGIN_LABELS,
  MovementValuation,
  MovementValuationParams,
  VALUATION_SOURCE_OPTIONS,
} from '../../models/movement-valuation';
import { MovementValuationApiService } from '../../services/movement-valuation-api.service';

export const INVALID_RANGE_MESSAGE = 'La fecha final no puede ser anterior a la inicial.';

/** Movimientos valorados: consulta de solo lectura por producto, origen y fecha (módulo Costeo). */
@Component({
  selector: 'app-valuation-movements',
  templateUrl: './valuation-movements.component.html',
  styleUrl: './valuation-movements.component.scss',
  imports: [RouterLink, NgxDatatableModule, ReactiveFormsModule, DatePipe, MoneyPipe],
})
export class ValuationMovementsComponent implements OnInit {
  readonly pageSize = 10;
  readonly messages = { emptyMessage: 'Sin movimientos valorados para los filtros elegidos.', totalMessage: 'en total' };
  readonly sourceOptions = VALUATION_SOURCE_OPTIONS;
  readonly filterForm = inject(FormBuilder).nonNullable.group({
    dateFrom: [''],
    dateTo: [''],
    productId: [''],
    sourceType: [''],
  });

  rows: MovementValuation[] = [];
  total = 0;
  /** Página actual base 0, como espera ngx-datatable. */
  pageIndex = 0;
  loading = false;
  errorMessage = '';
  rangeError = '';
  products: Product[] = [];

  private api = inject(MovementValuationApiService);
  private productsApi = inject(ProductsApiService);
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
            catchError((err: Error) => {
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

    this.filterForm.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.pageIndex = 0;
      if (this.validateRange()) {
        this.reload$.next();
      }
    });
    this.reload$.next();
  }

  originLabel(row: MovementValuation): string {
    return COST_ORIGIN_LABELS[row.costOrigin];
  }

  reload(): void {
    this.reload$.next();
  }

  clearFilters(): void {
    this.filterForm.setValue({ dateFrom: '', dateTo: '', productId: '', sourceType: '' });
  }

  onPage(event: { offset: number }): void {
    // ngx-datatable también emite `page` al inicializarse; sin cambio de página no se vuelve a pedir.
    if (event.offset === this.pageIndex) {
      return;
    }
    this.pageIndex = event.offset;
    this.reload$.next();
  }

  private validateRange(): boolean {
    const { dateFrom, dateTo } = this.filterForm.getRawValue();
    this.rangeError = dateFrom && dateTo && dateFrom > dateTo ? INVALID_RANGE_MESSAGE : '';
    return !this.rangeError;
  }

  private params(): MovementValuationParams {
    const { dateFrom, dateTo, productId, sourceType } = this.filterForm.getRawValue();
    return {
      dateFrom: dateFrom || undefined,
      dateTo: dateTo || undefined,
      productId: productId || undefined,
      sourceType: sourceType || undefined,
      page: this.pageIndex + 1,
      pageSize: this.pageSize,
    };
  }
}
