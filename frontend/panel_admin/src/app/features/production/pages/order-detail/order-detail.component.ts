import { BreakpointObserver } from '@angular/cdk/layout';
import { DatePipe, NgTemplateOutlet, formatDate } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { finalize, interval } from 'rxjs';
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
  releasing = false;
  /** Reloj del navegador, solo informativo: el servidor vuelve a validar el mínimo al liberar. */
  now = Date.now();
  readonly quantity = formatQuantity;
  readonly number = formatOrderNumber;

  ngOnInit(): void {
    this.breakpoints.observe(COMPACT_QUERY).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(state => this.compact = state.matches);
    interval(30000).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.now = Date.now());
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
      : status === 'refrigerating' ? 'PRODUCTION.ORDERS.STATUS.REFRIGERATING'
      : status === 'ready_to_pack' ? 'PRODUCTION.ORDERS.STATUS.READY_TO_PACK' : 'PRODUCTION.ORDERS.STATUS.IN_PREPARATION';
  }

  /** Muestra la sección de liberación (en refrigeración o ya lista para empacar). */
  get hasRelease(): boolean {
    return !!this.order?.release;
  }

  /** Primera hora habilitada (ISO) o `null`. */
  get releasableFrom(): string | null {
    return this.order?.release?.releasableFrom ?? null;
  }

  get canRelease(): boolean {
    const from = this.releasableFrom;
    return this.order?.status === 'refrigerating' && !!from && this.now >= Date.parse(from);
  }

  /** Tiempo transcurrido desde el ingreso a refrigeración, «Xh Ymin». */
  get elapsed(): string {
    const entered = this.order?.enteredAt;
    if (!entered) return '—';
    const end = this.order?.status === 'ready_to_pack' && this.order.releasedAt ? Date.parse(this.order.releasedAt) : this.now;
    const minutes = Math.max(0, Math.floor((end - Date.parse(entered)) / 60000));
    return tr('PRODUCTION.ORDERS.RELEASE.HOURS_MIN', { hours: Math.floor(minutes / 60), minutes: minutes % 60 });
  }

  formatDateTime(value: string): string {
    return formatDate(value, 'dd/MM/yyyy HH:mm', 'en-US');
  }

  async release(): Promise<void> {
    const order = this.order;
    if (!order || this.releasing || !this.canRelease) return;
    this.releasing = true;
    this.actionError = '';
    this.success = '';
    const result = await Swal.fire({
      title: tr('PRODUCTION.ORDERS.RELEASE.CONFIRM_TITLE', { lot: order.lot?.code ?? '' }),
      text: tr('PRODUCTION.ORDERS.RELEASE.CONFIRM_TEXT', {
        quantity: formatQuantity(order.actualOutput ?? '0'), unit: order.resultProduct.unit?.abbreviation ?? '' }),
      showCancelButton: true, confirmButtonText: tr('PRODUCTION.ORDERS.RELEASE.ACTION'), cancelButtonText: tr('COMMON.CANCELAR'),
    });
    if (!result.isConfirmed || this.destroyRef.destroyed) { this.releasing = false; return; }
    this.api.release(order.id).pipe(finalize(() => this.releasing = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: released => { this.order = released; this.success = tr('PRODUCTION.ORDERS.RELEASE.DONE'); },
      error: (error: OrderApiError) => {
        const from = error.fields.releasableFrom;
        this.actionError = error.fields.code === 'release_too_early' && from
          ? tr('PRODUCTION.ORDERS.RELEASE.TOO_EARLY', { date: this.formatDateTime(from) }) : error.message;
        if (error.fields.code === 'release_too_early') this.load();
      },
    });
  }

  get statusClass(): string {
    const status = this.order?.status;
    return status === 'draft' ? 'col-blue' : status === 'refrigerating' ? 'col-green' : status === 'ready_to_pack' ? 'col-purple' : 'col-orange';
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
