import { BreakpointObserver } from '@angular/cdk/layout';
import { DatePipe, NgTemplateOutlet } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { finalize } from 'rxjs';
import Swal from 'sweetalert2';
import { tr } from '../../../../core/i18n/translate';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { OrderApiError, ProductionOrder, formatOrderNumber } from '../../models/order';
import { formatQuantity } from '../../models/recipe';
import { OrdersApiService } from '../../services/orders-api.service';

/** Por debajo de 957 px el detalle pasa a filas «etiqueta | valor» y a tarjetas de ingredientes. */
export const COMPACT_QUERY = '(max-width: 956.98px)';

@Component({
  selector: 'app-order-detail',
  imports: [TranslatePipe, RouterLink, DatePipe, NgTemplateOutlet, MoneyPipe],
  templateUrl: './order-detail.component.html',
  styleUrl: './order-detail.component.scss',
})
export class OrderDetailComponent implements OnInit {
  private api = inject(OrdersApiService);
  private route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);
  private breakpoints = inject(BreakpointObserver);
  /** Pantalla estrecha (< 957 px). */
  compact = false;
  order: ProductionOrder | null = null;
  loading = true;
  starting = false;
  error = '';
  actionError = '';
  success = '';
  readonly quantity = formatQuantity;
  readonly number = formatOrderNumber;

  ngOnInit(): void {
    this.breakpoints.observe(COMPACT_QUERY).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(state => this.compact = state.matches);
    this.load();
  }

  load(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    this.loading = true;
    this.error = '';
    this.api.get(id).pipe(finalize(() => this.loading = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: order => this.order = order,
      error: (error: OrderApiError) => this.error = error.message,
    });
  }

  get statusKey(): string {
    const status = this.order?.status;
    return status === 'draft' ? 'PRODUCTION.ORDERS.STATUS.DRAFT'
      : status === 'refrigerating' ? 'PRODUCTION.ORDERS.STATUS.REFRIGERATING' : 'PRODUCTION.ORDERS.STATUS.IN_PREPARATION';
  }

  get statusClass(): string {
    const status = this.order?.status;
    return status === 'draft' ? 'col-blue' : status === 'refrigerating' ? 'col-green' : 'col-orange';
  }

  async start(): Promise<void> {
    const order = this.order;
    if (!order || this.starting || order.status !== 'draft') return;
    this.starting = true;
    this.actionError = '';
    this.success = '';
    const result = await Swal.fire({
      title: tr('PRODUCTION.ORDERS.CONFIRM_START_TITLE', { number: formatOrderNumber(order.number) }),
      text: tr('PRODUCTION.ORDERS.CONFIRM_START_TEXT'),
      showCancelButton: true, confirmButtonText: tr('PRODUCTION.ORDERS.START'), cancelButtonText: tr('COMMON.CANCELAR'),
    });
    if (!result.isConfirmed || this.destroyRef.destroyed) { this.starting = false; return; }
    this.api.start(order.id).pipe(finalize(() => this.starting = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: started => { this.order = started; this.success = tr('PRODUCTION.ORDERS.STARTED'); },
      error: (error: OrderApiError) => this.actionError = error.fields.warehouseId ?? error.message,
    });
  }
}
