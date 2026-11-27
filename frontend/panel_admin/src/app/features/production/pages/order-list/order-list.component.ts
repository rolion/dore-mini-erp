import { BreakpointObserver } from '@angular/cdk/layout';
import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { tr } from '../../../../core/i18n/translate';
import { EMPTY, Subject, catchError, finalize, startWith, switchMap, throwError } from 'rxjs';
import { OrderApiError, OrderListParams, OrderStatus, OrderStatusFilter, ProductionOrder, formatOrderNumber } from '../../models/order';
import { Recipe, formatQuantity } from '../../models/recipe';
import { OrderFiltersState, OrdersApiService } from '../../services/orders-api.service';
import { RecipesApiService } from '../../services/recipes-api.service';

/** Por debajo de 957 px la lista pasa a tarjetas. */
export const COMPACT_QUERY = '(max-width: 956.98px)';

@Component({
  selector: 'app-order-list',
  imports: [TranslatePipe, ReactiveFormsModule, RouterLink, NgbPagination, DatePipe],
  templateUrl: './order-list.component.html',
  styleUrl: './order-list.component.scss',
})
export class OrderListComponent implements OnInit {
  readonly state = inject(OrderFiltersState);
  private api = inject(OrdersApiService);
  private recipesApi = inject(RecipesApiService);
  private destroyRef = inject(DestroyRef);
  private breakpoints = inject(BreakpointObserver);
  /** Pantalla estrecha (< 957 px): tarjetas en lugar de tabla. */
  compact = false;
  private reload$ = new Subject<void>();
  status = new FormControl<OrderStatusFilter>(this.state.status, { nonNullable: true });
  /** Sin un FormGroup el navegador enviaría el formulario y recargaría la página (perdiendo el filtro). */
  recipe = new FormControl(this.state.recipeId, { nonNullable: true });
  dateFrom = new FormControl(this.state.dateFrom, { nonNullable: true });
  dateTo = new FormControl(this.state.dateTo, { nonNullable: true });
  readonly filters = new FormGroup({ status: this.status, recipe: this.recipe, dateFrom: this.dateFrom, dateTo: this.dateTo });
  recipes: Recipe[] = [];
  /** Desde posterior a Hasta: no se consulta (EDGE-01). */
  rangeInvalid = false;
  rows: ProductionOrder[] = [];
  total = 0;
  pageSize = 20;
  loading = false;
  error = '';
  readonly quantity = formatQuantity;
  readonly number = formatOrderNumber;

  ngOnInit(): void {
    this.recipesApi.list({ status: 'all', pageSize: 100 }).pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: page => this.recipes = page.results, error: () => this.recipes = [] });
    this.breakpoints.observe(COMPACT_QUERY).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(state => this.compact = state.matches);
    this.reload$.pipe(startWith(undefined), switchMap(() => {
      this.loading = true;
      this.error = '';
      const params: OrderListParams = {
        status: this.state.status, recipeId: this.state.recipeId, dateFrom: this.state.dateFrom, dateTo: this.state.dateTo,
        page: this.state.pageIndex + 1, pageSize: this.pageSize,
      };
      return this.api.list(params).pipe(
        catchError((error: OrderApiError) => {
          if (!error.invalidPage || this.state.pageIndex === 0) return throwError(() => error);
          this.state.pageIndex = 0;
          return this.api.list({ ...params, page: 1 });
        }),
        catchError((error: OrderApiError) => { this.error = error.message; this.rows = []; this.total = 0; return EMPTY; }),
        finalize(() => this.loading = false));
    }), takeUntilDestroyed(this.destroyRef)).subscribe(page => { this.rows = page.results; this.total = page.count; });
  }

  reload(): void { this.reload$.next(); }

  onPage(page: number): void {
    if (this.loading || page - 1 === this.state.pageIndex) return;
    this.state.pageIndex = page - 1;
    this.reload();
  }

  get isDefaultFilter(): boolean {
    return this.state.status === 'all' && !this.state.recipeId && !this.state.dateFrom && !this.state.dateTo;
  }

  get hasPendingFilters(): boolean {
    return this.status.value !== 'all' || !!this.recipe.value || !!this.dateFrom.value || !!this.dateTo.value;
  }

  /** Etiquetas de los filtros vigentes (para el estado vacío con filtros). */
  get activeFilters(): string[] {
    const labels: string[] = [];
    if (this.state.status !== 'all') labels.push(tr(this.statusKey(this.state.status)));
    const recipe = this.recipes.find(item => item.id === this.state.recipeId);
    if (this.state.recipeId) labels.push(recipe?.name ?? this.state.recipeId);
    if (this.state.dateFrom) labels.push(`${tr('COMMON.DESDE')}: ${this.state.dateFrom}`);
    if (this.state.dateTo) labels.push(`${tr('COMMON.HASTA')}: ${this.state.dateTo}`);
    return labels;
  }

  applyFilters(): void {
    this.rangeInvalid = !!this.dateFrom.value && !!this.dateTo.value && this.dateFrom.value > this.dateTo.value;
    if (this.rangeInvalid) return;
    this.state.status = this.status.value;
    this.state.recipeId = this.recipe.value;
    this.state.dateFrom = this.dateFrom.value;
    this.state.dateTo = this.dateTo.value;
    this.state.pageIndex = 0;
    this.reload();
  }

  clearFilters(): void {
    this.filters.reset({ status: 'all', recipe: '', dateFrom: '', dateTo: '' }, { emitEvent: false });
    this.applyFilters();
  }

  /** «—» cuando no hay dato; cantidad con unidad en otro caso. */
  amount(value: string | null | undefined, unit: string | null | undefined): string {
    return value == null ? '—' : `${formatQuantity(value)} ${unit ?? ''}`.trim();
  }

  statusClass(status: OrderStatus): string { return status === 'draft' ? 'col-blue' : status === 'in_preparation' ? 'col-orange' : status === 'ready_to_pack' ? 'col-purple' : 'col-green'; }

  statusKey(status: OrderStatus): string {
    return status === 'draft' ? 'PRODUCTION.ORDERS.STATUS.DRAFT'
      : status === 'in_preparation' ? 'PRODUCTION.ORDERS.STATUS.IN_PREPARATION'
      : status === 'ready_to_pack' ? 'PRODUCTION.ORDERS.STATUS.READY_TO_PACK' : 'PRODUCTION.ORDERS.STATUS.REFRIGERATING';
  }
}
