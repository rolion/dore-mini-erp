import { AsyncPipe, DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgSelectComponent } from '@ng-select/ng-select';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { ToastrService } from 'ngx-toastr';
import { EMPTY, Observable, Subject, catchError, concat, debounceTime, distinctUntilChanged, finalize, switchMap, tap } from 'rxjs';
import { OrderStatusBadgeComponent } from '../../components/order-status-badge/order-status-badge.component';
import { PaymentStatusBadgeComponent } from '../../components/payment-status-badge/payment-status-badge.component';
import {
  ORDER_STATUSES,
  ORDER_STATUS_LABELS,
  OrderApiError,
  OrderCustomer,
  OrderSummary,
  PAYMENT_STATUSES,
  PAYMENT_STATUS_LABELS,
  SALES_CHANNELS,
  SALES_CHANNEL_LABELS,
  ZERO_AMOUNT,
} from '../../models/order';
import { MoneyPipe } from '../../pipes/money.pipe';
import { CustomerOptionsService } from '../../services/customer-options.service';
import { OrdersApiService } from '../../services/orders-api.service';
import {
  DEFAULT_FILTERS,
  ListFilters,
  ListState,
  SHORTCUTS,
  Shortcut,
  activeShortcut,
  hasActiveFilters,
  parseState,
  serializeState,
  toListParams,
} from './order-list-filters';

export const PAGE_SIZE = 10;
export const EMPTY_FILTERED = 'No hay pedidos que coincidan con los filtros.';
export const EMPTY_ALL = 'Aún no hay pedidos.';

/** Lista operativa de pedidos. La URL es la fuente de verdad de filtros y página, así se conservan al volver del detalle. */
@Component({
  selector: 'app-order-list',
  templateUrl: './order-list.component.html',
  styleUrl: './order-list.component.scss',
  imports: [
    RouterLink,
    DatePipe,
    AsyncPipe,
    NgxDatatableModule,
    ReactiveFormsModule,
    NgSelectComponent,
    MoneyPipe,
    OrderStatusBadgeComponent,
    PaymentStatusBadgeComponent,
  ],
})
export class OrderListComponent implements OnInit {
  readonly pageSize = PAGE_SIZE;
  readonly shortcuts = SHORTCUTS;
  readonly statusOptions = [
    { value: 'ALL', label: 'Todos' },
    { value: 'PENDING_DELIVERY', label: 'Pendientes de entrega' },
    ...ORDER_STATUSES.map((value) => ({ value, label: ORDER_STATUS_LABELS[value] })),
    { value: 'NOT_CANCELLED', label: 'No cancelados' },
  ];
  readonly paymentOptions = [
    { value: 'ALL', label: 'Todos' },
    ...PAYMENT_STATUSES.map((value) => ({ value, label: PAYMENT_STATUS_LABELS[value] })),
    { value: 'WITH_BALANCE', label: 'Con saldo pendiente' },
  ];
  readonly channelOptions = SALES_CHANNELS.map((value) => ({ value, label: SALES_CHANNEL_LABELS[value] }));
  readonly channelLabels = SALES_CHANNEL_LABELS;

  readonly filterForm = inject(FormBuilder).nonNullable.group({
    statusKey: [DEFAULT_FILTERS.statusKey],
    paymentKey: [DEFAULT_FILTERS.paymentKey],
    channel: [DEFAULT_FILTERS.channel],
    customer: [DEFAULT_FILTERS.customer as OrderCustomer | null],
    dateField: [DEFAULT_FILTERS.dateField],
    dateFrom: [DEFAULT_FILTERS.dateFrom],
    dateTo: [DEFAULT_FILTERS.dateTo],
  });

  rows: OrderSummary[] = [];
  total = 0;
  /** Página actual base 0, como espera ngx-datatable. */
  pageIndex = 0;
  loading = false;
  emptyMessage = EMPTY_ALL;
  ordering: 'newest' | 'expected' = 'newest';

  readonly customerInput$ = new Subject<string>();
  customersLoading = false;
  readonly customers$: Observable<OrderCustomer[]>;

  private api = inject(OrdersApiService);
  private customerOptions = inject(CustomerOptionsService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<ListState>();

  constructor() {
    this.customers$ = concat(
      this.customerOptions.search(''),
      this.customerInput$.pipe(
        debounceTime(300),
        distinctUntilChanged(),
        tap(() => (this.customersLoading = true)),
        switchMap((term) => this.customerOptions.search(term).pipe(finalize(() => (this.customersLoading = false)))),
      ),
    );
    this.destroyRef.onDestroy(() => this.customerInput$.complete());
  }

  get messages(): { emptyMessage: string; totalMessage: string } {
    return { emptyMessage: this.emptyMessage, totalMessage: 'en total' };
  }

  get currentShortcut(): Shortcut['id'] | null {
    return activeShortcut(this.filterForm.getRawValue());
  }

  get filtersActive(): boolean {
    return hasActiveFilters(this.filterForm.getRawValue());
  }

  ngOnInit(): void {
    this.reload$
      .pipe(
        switchMap((state) => {
          this.loading = true;
          return this.api.list(toListParams(state, this.pageSize)).pipe(
            catchError((err: OrderApiError) => {
              this.toastr.error(err.message);
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

    // La URL manda: cada cambio de filtros navega y esta suscripción aplica el estado y recarga.
    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const state = parseState(params);
      const { page, ...filters } = state;
      this.filterForm.setValue(filters, { emitEvent: false });
      this.pageIndex = page - 1;
      this.emptyMessage = hasActiveFilters(filters) ? EMPTY_FILTERED : EMPTY_ALL;
      this.ordering = state.statusKey === 'PENDING_DELIVERY' ? 'expected' : 'newest';
      this.reload$.next(state);
    });

    this.filterForm.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.navigate(this.filterForm.getRawValue(), 1));
  }

  applyShortcut(shortcut: Shortcut): void {
    this.filterForm.patchValue({ statusKey: shortcut.statusKey, paymentKey: shortcut.paymentKey });
  }

  clearFilters(): void {
    this.filterForm.setValue({ ...DEFAULT_FILTERS });
  }

  onPage(event: { offset: number }): void {
    // ngx-datatable también emite `page` al inicializarse; sin cambio de página no se vuelve a pedir.
    if (event.offset === this.pageIndex) {
      return;
    }
    this.navigate(this.filterForm.getRawValue(), event.offset + 1);
  }

  /** Saldo en rojo solo si hay deuda en un pedido que sigue vivo. */
  owes(row: OrderSummary): boolean {
    return row.status !== 'CANCELLED' && row.balance !== ZERO_AMOUNT;
  }

  /** Un cancelado sin pagos no tiene nada que mostrar en el saldo. */
  showsBalance(row: OrderSummary): boolean {
    return !(row.status === 'CANCELLED' && row.paidTotal === ZERO_AMOUNT);
  }

  private navigate(filters: ListFilters, page: number): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: serializeState({ ...filters, page }),
      replaceUrl: true,
    });
  }
}
