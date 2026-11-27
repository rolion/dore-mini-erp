import { BreakpointObserver } from '@angular/cdk/layout';
import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { EMPTY, Subject, catchError, finalize, startWith, switchMap, throwError } from 'rxjs';
import { OrderApiError, OrderStatus, OrderStatusFilter, ProductionOrder, formatOrderNumber } from '../../models/order';
import { formatQuantity } from '../../models/recipe';
import { OrderFiltersState, OrdersApiService } from '../../services/orders-api.service';

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
  private destroyRef = inject(DestroyRef);
  private breakpoints = inject(BreakpointObserver);
  /** Pantalla estrecha (< 957 px): tarjetas en lugar de tabla. */
  compact = false;
  private reload$ = new Subject<void>();
  status = new FormControl<OrderStatusFilter>(this.state.status, { nonNullable: true });
  /** Sin un FormGroup el navegador enviaría el formulario y recargaría la página (perdiendo el filtro). */
  readonly filters = new FormGroup({ status: this.status });
  rows: ProductionOrder[] = [];
  total = 0;
  pageSize = 20;
  loading = false;
  error = '';
  readonly quantity = formatQuantity;
  readonly number = formatOrderNumber;

  ngOnInit(): void {
    this.breakpoints.observe(COMPACT_QUERY).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(state => this.compact = state.matches);
    this.reload$.pipe(startWith(undefined), switchMap(() => {
      this.loading = true;
      this.error = '';
      const params = { status: this.state.status, page: this.state.pageIndex + 1, pageSize: this.pageSize };
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

  get isDefaultFilter(): boolean { return this.state.status === 'all'; }

  applyFilters(): void {
    this.state.status = this.status.value;
    this.state.pageIndex = 0;
    this.reload();
  }

  clearFilters(): void {
    this.status.setValue('all', { emitEvent: false });
    this.applyFilters();
  }

  statusClass(status: OrderStatus): string { return status === 'draft' ? 'col-blue' : status === 'in_preparation' ? 'col-orange' : 'col-green'; }

  statusKey(status: OrderStatus): string {
    return status === 'draft' ? 'PRODUCTION.ORDERS.STATUS.DRAFT'
      : status === 'in_preparation' ? 'PRODUCTION.ORDERS.STATUS.IN_PREPARATION' : 'PRODUCTION.ORDERS.STATUS.REFRIGERATING';
  }
}
