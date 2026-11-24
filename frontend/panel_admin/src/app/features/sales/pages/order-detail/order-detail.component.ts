import { tr } from '../../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { DatePipe } from '@angular/common';
import { Component, DestroyRef, ElementRef, OnInit, inject, viewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { PostingIssuesAlertComponent } from '../../../../shared/components/posting-issues-alert/posting-issues-alert.component';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { EMPTY, Observable, catchError, finalize, firstValueFrom, switchMap, tap } from 'rxjs';
import Swal from 'sweetalert2';
import {
  AddItemEvent,
  OrderItemsComponent,
  QuantityChangeEvent,
} from '../../components/order-items/order-items.component';
import {
  DeliveryDialogComponent,
  STALE_ORDER,
} from '../../components/delivery-dialog/delivery-dialog.component';
import { OrderReversalCardComponent } from '../../components/order-reversal-card/order-reversal-card.component';
import {
  ReturnDialogComponent,
  STALE_ORDER_FOR_RETURN,
} from '../../components/return-dialog/return-dialog.component';
import { OrderPaymentsComponent } from '../../components/order-payments/order-payments.component';
import {
  PaymentDialogComponent,
  STALE_ORDER_FOR_PAYMENT,
} from '../../components/payment-dialog/payment-dialog.component';
import { OrderStatusBadgeComponent } from '../../components/order-status-badge/order-status-badge.component';
import { OrderSummaryComponent } from '../../components/order-summary/order-summary.component';
import { PaymentStatusBadgeComponent } from '../../components/payment-status-badge/payment-status-badge.component';
import { StockOutputCardComponent } from '../../components/stock-output-card/stock-output-card.component';
import {
  DeliveryPreview,
  FieldErrors,
  ReturnPreview,
  Order,
  OrderApiError,
  OrderItem,
  OrderRuleError,
  PostingIssue,
  PaymentInput,
  SALES_CHANNEL_LABELS,
  hasBalance,
  todayIso,
} from '../../models/order';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { OrdersApiService } from '../../services/orders-api.service';

type PrimaryAction = 'prepare' | 'ready' | 'deliver';

const PRIMARY_ORDER: readonly PrimaryAction[] = ['prepare', 'ready', 'deliver'];
export const PRIMARY_LABELS: Record<PrimaryAction, string> = {
  get prepare() { return tr('SALES.ORDER_DETAIL.INICIAR_PREPARACION'); },
  get ready() { return tr('SALES.ORDER_DETAIL.MARCAR_LISTO'); },
  get deliver() { return tr('SALES.ORDER_DETAIL.MARCAR_ENTREGADO'); },
};
const OPEN_STATUSES: readonly string[] = ['NEW', 'IN_PREPARATION', 'READY'];
/** Estados con la vista de consulta (acciones en la cabecera y pago en un modal); solo NEW aún se arma. */
const COMPACT_STATUSES: readonly string[] = ['IN_PREPARATION', 'READY', 'DELIVERED', 'CANCELLED', 'RETURNED'];

/** Pantalla de trabajo del pedido. Las acciones visibles salen del servidor; los importes no se calculan aquí. */
@Component({
  selector: 'app-order-detail',
  templateUrl: './order-detail.component.html',
  styleUrl: './order-detail.component.scss',
  imports: [TranslatePipe, 
    RouterLink,
    PostingIssuesAlertComponent,
    DatePipe,
    MoneyPipe,
    OrderStatusBadgeComponent,
    PaymentStatusBadgeComponent,
    OrderItemsComponent,
    OrderSummaryComponent,
    OrderPaymentsComponent,
    StockOutputCardComponent,
    OrderReversalCardComponent,
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
  /** Faltantes de configuración contable que bloquearon la última acción (confirmar o cobrar). */
  postingIssues: PostingIssue[] = [];

  private api = inject(OrdersApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private modal = inject(NgbModal);
  private destroyRef = inject(DestroyRef);
  private payments = viewChild(OrderPaymentsComponent);
  private paymentsHost = viewChild(OrderPaymentsComponent, { read: ElementRef });

  /** Id del pedido de la URL; cambia si se navega a otro pedido sin salir de esta pantalla. */
  private orderId = '';

  ngOnInit(): void {
    // El componente se reutiliza al cambiar solo el id de la ruta: se vuelve a cargar y se descarta el estado anterior.
    this.route.paramMap
      .pipe(
        tap((params) => {
          this.orderId = params.get('id') ?? '';
          this.order = null;
          this.loading = true;
          this.fieldErrors = {};
          this.busy = false;
        }),
        switchMap(() =>
          this.api.get(this.orderId).pipe(
            catchError((err: OrderApiError) => {
              this.loading = false;
              this.toastr.error(err.message);
              this.router.navigate(['/pocketbiz/sales/orders']);
              return EMPTY;
            }),
          ),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((order) => {
        this.order = order;
        this.loading = false;
      });
  }

  get primaryAction(): PrimaryAction | null {
    const allowed = this.order?.allowedTransitions ?? [];
    return PRIMARY_ORDER.find((action) => allowed.includes(action)) ?? null;
  }

  get canCancel(): boolean {
    return !!this.order?.allowedTransitions.includes('cancel');
  }

  get canReturn(): boolean {
    return !!this.order?.allowedTransitions.includes('return');
  }

  get returned(): boolean {
    return this.order?.status === 'RETURNED';
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

  /** Vista de consulta del pedido ya confirmado (IN_PREPARATION, READY, DELIVERED). */
  get compactLayout(): boolean {
    return !!this.order && COMPACT_STATUSES.includes(this.order.status);
  }

  get cancelled(): boolean {
    return this.order?.status === 'CANCELLED';
  }

  /** «Registrar pago» de la tarjeta Cobro: abre el formulario de Pagos, lo deja a la vista y enfoca el monto. */
  openPayment(): void {
    if (this.compactLayout) {
      void this.openPaymentDialog();
      return;
    }
    this.payments()?.open();
    const host = this.paymentsHost()?.nativeElement as HTMLElement | undefined;
    host?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setTimeout(() => host?.querySelector<HTMLInputElement>('#payment-amount')?.focus());
  }

  runPrimary(): void {
    const order = this.order;
    switch (this.primaryAction) {
      case 'prepare':
        return this.run(() => this.api.prepare(order!.id), tr('SALES.ORDER_DETAIL.PEDIDO_EN_PREPARACION'));
      case 'ready':
        return this.run(() => this.api.ready(order!.id), tr('SALES.ORDER_DETAIL.PEDIDO_LISTO'));
      case 'deliver':
        void this.deliver();
        return;
    }
  }

  async deliver(): Promise<void> {
    const order = this.order;
    if (!order || this.busy) return;
    this.busy = true;
    let preview: DeliveryPreview;
    try {
      preview = await firstValueFrom(this.api.deliveryPreview(order.id));
    } catch (err) {
      this.busy = false;
      this.onError(err as OrderApiError);
      return;
    }
    this.busy = false;
    if (preview.requiresStockOutput) {
      await this.deliverWithStock(order, preview);
      return;
    }
    const deliveredDate = await this.askDeliveryDate(order);
    if (deliveredDate !== null) {
      this.run(() => this.api.deliver(order.id, deliveredDate), tr('SALES.ORDER_DETAIL.PEDIDO_ENTREGADO'));
    }
  }

  async cancel(): Promise<void> {
    const order = this.order;
    if (!order) return;
    const reason = await this.askCancelReason(order);
    if (reason === null) return;
    // Con cobros, la persona confirma que el dinero ya se devolvió fuera de PocketBiz (el servidor lo exige).
    const refund = order.payments.length > 0;
    if (refund && !(await this.confirmRefund(order))) return;
    this.run(() => this.api.cancel(order.id, reason, refund), tr('SALES.ORDER_DETAIL.PEDIDO_CANCELADO_2'));
  }

  /** «Registrar devolución» (pedido entregado): lee el efecto y abre el diálogo de confirmación. */
  async registerReturn(): Promise<void> {
    const order = this.order;
    if (!order || this.busy) return;
    this.busy = true;
    let preview: ReturnPreview;
    try {
      preview = await firstValueFrom(this.api.returnPreview(order.id));
    } catch (err) {
      this.busy = false;
      this.onError(err as OrderApiError);
      return;
    }
    this.busy = false;
    const ref = this.modal.open(ReturnDialogComponent, { size: 'lg', backdrop: 'static', keyboard: false });
    (ref.componentInstance as ReturnDialogComponent).init(order, preview);
    try {
      this.order = (await ref.result) as Order;
      this.toastr.success(tr('SALES.ORDER_RETURN.PEDIDO_DEVUELTO'));
    } catch (reason) {
      // Cerrar no cambia nada; si el pedido cambió en otra parte, se vuelve a leer.
      if (reason === STALE_ORDER_FOR_RETURN) {
        this.toastr.error(tr('SALES.ORDER_DETAIL.EL_PEDIDO_CAMBIO_DESDE_QUE'));
        this.reload();
      }
    }
  }

  addItem(event: AddItemEvent): void {
    this.run(() => this.api.addItem(this.order!.id, event.productId, event.quantity), tr('SALES.ORDER_DETAIL.PRODUCTO_AGREGADO'));
  }

  changeQuantity(event: QuantityChangeEvent): void {
    this.run(() => this.api.changeItemQuantity(this.order!.id, event.item.id, event.quantity));
  }

  async removeItem(item: OrderItem): Promise<void> {
    const order = this.order;
    if (!order || !(await this.confirmRemove(item))) return;
    this.run(() => this.api.removeItem(order.id, item.id), tr('SALES.ORDER_DETAIL.PRODUCTO_QUITADO'));
  }

  applyDiscount(discount: string): void {
    this.run(() => this.api.applyDiscount(this.order!.id, discount), tr('SALES.ORDER_DETAIL.DESCUENTO_APLICADO'));
  }

  registerPayment(input: PaymentInput): void {
    this.run(() => this.api.registerPayment(this.order!.id, input), tr('PURCHASES.PURCHASE_PAYMENTS_TAB.PAGO_REGISTRADO'));
  }

  /** «Registrar pago» en la vista de consulta: modal que registra el pago y devuelve el pedido actualizado. */
  protected async openPaymentDialog(): Promise<void> {
    const order = this.order;
    if (!order || this.busy) return;
    const ref = this.modal.open(PaymentDialogComponent, { backdrop: 'static', keyboard: false });
    (ref.componentInstance as PaymentDialogComponent).init(order);
    try {
      this.order = (await ref.result) as Order;
      this.toastr.success(tr('PURCHASES.PURCHASE_PAYMENTS_TAB.PAGO_REGISTRADO'));
    } catch (reason) {
      // Cerrar no cambia nada; si el pedido cambió en otra parte, se vuelve a leer.
      if (reason === STALE_ORDER_FOR_PAYMENT) {
        this.toastr.error(tr('SALES.PAYMENT_DIALOG.PEDIDO_CAMBIO'));
        this.reload();
      }
    }
  }

  /** Entrega con salida de inventario: el diálogo elige almacén y confirma; devuelve el pedido entregado. */
  protected async deliverWithStock(order: Order, preview: DeliveryPreview): Promise<void> {
    const ref = this.modal.open(DeliveryDialogComponent, { size: 'lg', backdrop: 'static', keyboard: false });
    (ref.componentInstance as DeliveryDialogComponent).init(order, preview);
    try {
      this.order = (await ref.result) as Order;
      this.toastr.success(tr('SALES.ORDER_DETAIL.PEDIDO_ENTREGADO'));
    } catch (reason) {
      // Cancelar no cambia nada; si el pedido cambió en otra parte, se vuelve a leer.
      if (reason === STALE_ORDER) {
        this.toastr.error(tr('SALES.ORDER_DETAIL.EL_PEDIDO_CAMBIO_DESDE_QUE'));
        this.reload();
      }
    }
  }

  /** Diálogo de entrega: fecha real (hoy por defecto) y aviso de saldo que no bloquea. `null` = cancelado. */
  protected async askDeliveryDate(order: Order): Promise<string | null> {
    const result = await Swal.fire({
      title: tr('SALES.ORDER_DETAIL.MARCAR_COMO_ENTREGADO'),
      text: hasBalance(order) ? tr('SALES.ORDER_DETAIL.QUEDARA_UN_SALDO_DE_BS', { p0: order.balance }) : undefined,
      input: 'date',
      inputLabel: tr('SALES.ORDER_DETAIL.FECHA_DE_ENTREGA'),
      inputValue: todayIso(),
      inputAttributes: { max: todayIso() },
      inputValidator: (value) => (value ? null : tr('SALES.ORDER_DETAIL.LA_FECHA_DE_ENTREGA_ES')),
      showCancelButton: true,
      confirmButtonColor: '#8963ff',
      cancelButtonColor: '#fb7823',
      confirmButtonText: tr('SALES.ORDER_DETAIL.MARCAR_ENTREGADO'),
      cancelButtonText: tr('PERSONNEL.PROFILE_CONFIRMATION.VOLVER'),
    });
    return result.isConfirmed ? String(result.value) : null;
  }

  /** Diálogo de cancelación con motivo obligatorio. `null` = el usuario volvió atrás. */
  protected async askCancelReason(order: Order): Promise<string | null> {
    const result = await Swal.fire({
      title: tr('SALES.ORDER_DETAIL.CANCELAR_PEDIDO_2'),
      text: order.payments.length
        ? tr('SALES.ORDER_DETAIL.LOS_PAGOS_REGISTRADOS_NO_SE')
        : tr('SALES.ORDER_DETAIL.EL_PEDIDO_QUEDARA_CANCELADO_Y'),
      input: 'textarea',
      inputLabel: tr('SALES.ORDER_DETAIL.MOTIVO_DE_LA_CANCELACION'),
      inputAttributes: { maxlength: '500' },
      inputValidator: (value) => (value?.trim() ? null : tr('INVENTORY.ADJUSTMENT_FORM.EL_MOTIVO_ES_OBLIGATORIO')),
      showCancelButton: true,
      confirmButtonColor: '#dc3545',
      cancelButtonColor: '#fb7823',
      confirmButtonText: tr('SALES.ORDER_DETAIL.CANCELAR_PEDIDO_2'),
      cancelButtonText: tr('PERSONNEL.PROFILE_CONFIRMATION.VOLVER'),
    });
    return result.isConfirmed ? String(result.value).trim() : null;
  }

  /** Confirmación del reembolso externo antes de cancelar un pedido con cobros. */
  protected async confirmRefund(order: Order): Promise<boolean> {
    const result = await Swal.fire({
      title: tr('SALES.ORDER_RETURN.CANCELAR_COBROS_TITULO'),
      text: tr('SALES.ORDER_RETURN.CANCELAR_COBROS_TEXTO', { p0: order.paidTotal }),
      showCancelButton: true,
      confirmButtonColor: '#dc3545',
      cancelButtonColor: '#fb7823',
      confirmButtonText: tr('SALES.ORDER_RETURN.CANCELAR_COBROS_CONFIRMAR'),
      cancelButtonText: tr('PERSONNEL.PROFILE_CONFIRMATION.VOLVER'),
    });
    return result.isConfirmed;
  }

  protected async confirmRemove(item: OrderItem): Promise<boolean> {
    const result = await Swal.fire({
      titleText: tr('SALES.ORDER_DETAIL.QUITAR', { p0: item.productName }),
      showCancelButton: true,
      confirmButtonColor: '#8963ff',
      cancelButtonColor: '#fb7823',
      confirmButtonText: tr('SALES.ORDER_DETAIL.QUITAR_2'),
      cancelButtonText: tr('CUSTOMERS.CUSTOMER_QUICK_CREATE.CANCELAR'),
    });
    return result.isConfirmed;
  }

  /** Vuelve a leer el pedido actual tras un conflicto; si falla, se avisa y se conserva lo que ya se mostraba. */
  private reload(): void {
    this.api
      .get(this.orderId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (order) => (this.order = order),
        error: (err: OrderApiError) => this.toastr.error(err.message),
      });
  }

  /** Ejecuta una acción del servidor; si ya hay una en curso se ignora (sin ni siquiera construir la petición). */
  private run(request: () => Observable<Order>, successMessage?: string): void {
    if (this.busy) return;
    this.busy = true;
    this.fieldErrors = {};
    this.postingIssues = [];
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
    if (err instanceof OrderRuleError && err.postingIssues.length) {
      // Se explica en una alerta con enlace a la configuración, no solo en un aviso pasajero.
      this.postingIssues = err.postingIssues;
    } else {
      this.toastr.error(err.message);
    }
    if (err instanceof OrderRuleError) {
      // El estado del pedido pudo cambiar (otra pestaña, otro usuario): se vuelve a leer del servidor.
      this.reload();
    }
  }
}
