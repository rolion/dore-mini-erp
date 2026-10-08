import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { Observable, finalize } from 'rxjs';
import Swal from 'sweetalert2';
import {
  AddItemEvent,
  OrderItemsComponent,
  QuantityChangeEvent,
} from '../../components/order-items/order-items.component';
import { OrderPaymentsComponent } from '../../components/order-payments/order-payments.component';
import { OrderStatusBadgeComponent } from '../../components/order-status-badge/order-status-badge.component';
import { OrderSummaryComponent } from '../../components/order-summary/order-summary.component';
import { PaymentStatusBadgeComponent } from '../../components/payment-status-badge/payment-status-badge.component';
import {
  FieldErrors,
  Order,
  OrderApiError,
  OrderItem,
  OrderRuleError,
  PaymentInput,
  SALES_CHANNEL_LABELS,
  hasBalance,
  todayIso,
} from '../../models/order';
import { MoneyPipe } from '../../pipes/money.pipe';
import { OrdersApiService } from '../../services/orders-api.service';

type PrimaryAction = 'prepare' | 'ready' | 'deliver';

const PRIMARY_ORDER: readonly PrimaryAction[] = ['prepare', 'ready', 'deliver'];
export const PRIMARY_LABELS: Record<PrimaryAction, string> = {
  prepare: 'Iniciar preparación',
  ready: 'Marcar listo',
  deliver: 'Marcar entregado',
};
const OPEN_STATUSES: readonly string[] = ['NEW', 'IN_PREPARATION', 'READY'];

/** Pantalla de trabajo del pedido. Las acciones visibles salen del servidor; los importes no se calculan aquí. */
@Component({
  selector: 'app-order-detail',
  templateUrl: './order-detail.component.html',
  imports: [
    RouterLink,
    DatePipe,
    MoneyPipe,
    OrderStatusBadgeComponent,
    PaymentStatusBadgeComponent,
    OrderItemsComponent,
    OrderSummaryComponent,
    OrderPaymentsComponent,
  ],
})
export class OrderDetailComponent implements OnInit {
  readonly channelLabels = SALES_CHANNEL_LABELS;
  readonly primaryLabels = PRIMARY_LABELS;

  order: Order | null = null;
  loading = true;
  /** Una mutación en curso: bloquea los botones para no enviar dos veces. */
  busy = false;
  /** Errores de validación del servidor de la última acción, por campo. */
  fieldErrors: FieldErrors = {};

  private api = inject(OrdersApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.load();
  }

  get primaryAction(): PrimaryAction | null {
    const allowed = this.order?.allowedTransitions ?? [];
    return PRIMARY_ORDER.find((action) => allowed.includes(action)) ?? null;
  }

  get canCancel(): boolean {
    return !!this.order?.allowedTransitions.includes('cancel');
  }

  get hasBalance(): boolean {
    return !!this.order && hasBalance(this.order);
  }

  /** REQ-SAL-016: entregado no implica pagado. */
  get deliveredWithBalance(): boolean {
    return this.order?.status === 'DELIVERED' && this.hasBalance;
  }

  /** REQ-SAL-016: pagado no implica entregado. */
  get paidPendingDelivery(): boolean {
    return !!this.order && this.order.paymentStatus === 'PAID' && OPEN_STATUSES.includes(this.order.status);
  }

  get cancelled(): boolean {
    return this.order?.status === 'CANCELLED';
  }

  runPrimary(): void {
    const order = this.order;
    switch (this.primaryAction) {
      case 'prepare':
        return this.run(() => this.api.prepare(order!.id), 'Pedido en preparación');
      case 'ready':
        return this.run(() => this.api.ready(order!.id), 'Pedido listo');
      case 'deliver':
        void this.deliver();
        return;
    }
  }

  async deliver(): Promise<void> {
    const order = this.order;
    if (!order) return;
    const deliveredDate = await this.askDeliveryDate(order);
    if (deliveredDate !== null) {
      this.run(() => this.api.deliver(order.id, deliveredDate), 'Pedido entregado');
    }
  }

  async cancel(): Promise<void> {
    const order = this.order;
    if (!order) return;
    const reason = await this.askCancelReason(order);
    if (reason !== null) {
      this.run(() => this.api.cancel(order.id, reason), 'Pedido cancelado');
    }
  }

  addItem(event: AddItemEvent): void {
    this.run(() => this.api.addItem(this.order!.id, event.productId, event.quantity), 'Producto agregado');
  }

  changeQuantity(event: QuantityChangeEvent): void {
    this.run(() => this.api.changeItemQuantity(this.order!.id, event.item.id, event.quantity));
  }

  async removeItem(item: OrderItem): Promise<void> {
    const order = this.order;
    if (!order || !(await this.confirmRemove(item))) return;
    this.run(() => this.api.removeItem(order.id, item.id), 'Producto quitado');
  }

  applyDiscount(discount: string): void {
    this.run(() => this.api.applyDiscount(this.order!.id, discount), 'Descuento aplicado');
  }

  registerPayment(input: PaymentInput): void {
    this.run(() => this.api.registerPayment(this.order!.id, input), 'Pago registrado');
  }

  /** Diálogo de entrega: fecha real (hoy por defecto) y aviso de saldo que no bloquea. `null` = cancelado. */
  protected async askDeliveryDate(order: Order): Promise<string | null> {
    const result = await Swal.fire({
      title: 'Marcar como entregado',
      text: hasBalance(order) ? `Quedará un saldo de Bs ${order.balance} por cobrar.` : undefined,
      input: 'date',
      inputLabel: 'Fecha de entrega',
      inputValue: todayIso(),
      inputAttributes: { max: todayIso() },
      inputValidator: (value) => (value ? null : 'La fecha de entrega es obligatoria.'),
      showCancelButton: true,
      confirmButtonColor: '#8963ff',
      cancelButtonColor: '#fb7823',
      confirmButtonText: 'Marcar entregado',
      cancelButtonText: 'Volver',
    });
    return result.isConfirmed ? String(result.value) : null;
  }

  /** Diálogo de cancelación con motivo obligatorio. `null` = el usuario volvió atrás. */
  protected async askCancelReason(order: Order): Promise<string | null> {
    const result = await Swal.fire({
      title: 'Cancelar pedido',
      text: order.payments.length
        ? 'Los pagos registrados no se eliminan.'
        : 'El pedido quedará cancelado y no podrá continuar el flujo de entrega.',
      input: 'textarea',
      inputLabel: 'Motivo de la cancelación',
      inputAttributes: { maxlength: '500' },
      inputValidator: (value) => (value?.trim() ? null : 'El motivo es obligatorio.'),
      showCancelButton: true,
      confirmButtonColor: '#dc3545',
      cancelButtonColor: '#fb7823',
      confirmButtonText: 'Cancelar pedido',
      cancelButtonText: 'Volver',
    });
    return result.isConfirmed ? String(result.value).trim() : null;
  }

  protected async confirmRemove(item: OrderItem): Promise<boolean> {
    const result = await Swal.fire({
      title: `¿Quitar "${item.productName}"?`,
      showCancelButton: true,
      confirmButtonColor: '#8963ff',
      cancelButtonColor: '#fb7823',
      confirmButtonText: 'Quitar',
      cancelButtonText: 'Cancelar',
    });
    return result.isConfirmed;
  }

  private load(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    this.api
      .get(id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (order) => {
          this.order = order;
          this.loading = false;
        },
        error: (err: OrderApiError) => {
          this.loading = false;
          this.toastr.error(err.message);
          if (this.order === null) {
            this.router.navigate(['/sales/orders']);
          }
        },
      });
  }

  /** Ejecuta una acción del servidor; si ya hay una en curso se ignora (sin ni siquiera construir la petición). */
  private run(request: () => Observable<Order>, successMessage?: string): void {
    if (this.busy) return;
    this.busy = true;
    this.fieldErrors = {};
    request()
      .pipe(
        finalize(() => (this.busy = false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (order) => {
          this.order = order;
          if (successMessage) this.toastr.success(successMessage);
        },
        error: (err: OrderApiError) => this.onError(err),
      });
  }

  private onError(err: OrderApiError): void {
    if (err.status === 400 && Object.keys(err.fieldErrors).length) {
      // El pedido no cambió, pero lo escrito en un campo puede no coincidir ya con el servidor.
      this.fieldErrors = err.fieldErrors;
      return;
    }
    this.toastr.error(err.message);
    if (err instanceof OrderRuleError) {
      // El estado del pedido pudo cambiar (otra pestaña, otro usuario): se vuelve a leer del servidor.
      this.load();
    }
  }
}
