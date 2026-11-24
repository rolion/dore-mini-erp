import { tr } from '../../../core/i18n/translate';
import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import {
  DeliveryPreview,
  DeliveryPreviewDto,
  OrderReversal,
  OrderReversalDto,
  ReturnPreview,
  ReturnPreviewDto,
  FieldErrors,
  Order,
  OrderApiError,
  OrderDto,
  OrderErrorField,
  OrderInput,
  OrderItem,
  OrderItemDto,
  OrderListParams,
  OrderRuleError,
  PostingIssue,
  OrderSummary,
  OrderSummaryDto,
  Payment,
  PaymentDto,
  PaymentInput,
  StartOrderInput,
  StockOutput,
  StockOutputDto,
  StockShortage,
} from '../models/order';

export const NETWORK_ERROR_MESSAGE = (): string => tr('CUSTOMERS.CUSTOMERS_API_SERVICE.NO_SE_PUDO_CONECTAR_CON');
export const NOT_FOUND_MESSAGE = (): string => tr('SALES.ORDERS_API_SERVICE.PEDIDO_NO_ENCONTRADO');
export const GENERIC_ERROR_MESSAGE = (): string => tr('CUSTOMERS.CUSTOMERS_API_SERVICE.OCURRIO_UN_ERROR_INESPERADO_INTENTALO');
export const VALIDATION_ERROR_MESSAGE = (): string => tr('CUSTOMERS.CUSTOMERS_API_SERVICE.REVISA_LOS_DATOS_INGRESADOS');

const FIELD_NAMES: Record<string, OrderErrorField> = {
  customer_id: 'customerId',
  sales_channel: 'salesChannel',
  order_date: 'orderDate',
  expected_delivery_date: 'expectedDeliveryDate',
  notes: 'notes',
  product_id: 'productId',
  quantity: 'quantity',
  items: 'items',
  discount: 'discount',
  delivered_date: 'deliveredDate',
  warehouse_id: 'warehouseId',
  reason: 'reason',
  amount: 'amount',
  payment_method: 'paymentMethod',
  payment_date: 'paymentDate',
  reference: 'reference',
};

function toItem(dto: OrderItemDto): OrderItem {
  return {
    id: dto.id,
    productId: dto.product_id,
    productName: dto.product_name,
    unitPrice: dto.unit_price,
    quantity: dto.quantity,
    subtotal: dto.subtotal,
  };
}

function toPayment(dto: PaymentDto): Payment {
  return {
    id: dto.id,
    amount: dto.amount,
    paymentMethod: dto.payment_method,
    paymentDate: dto.payment_date,
    reference: dto.reference,
    createdAt: dto.created_at,
  };
}

function toStockOutput(dto: StockOutputDto | null | undefined): StockOutput | null {
  if (!dto) return null;
  return {
    reference: dto.reference,
    warehouseId: dto.warehouse.id,
    warehouseName: dto.warehouse.name,
    occurredAt: dto.occurred_at,
    userName: dto.user_name,
    movements: dto.movements.map((m) => ({
      id: m.id,
      productId: m.product.id,
      productName: m.product.name,
      quantity: m.quantity,
      unit: m.unit.abbreviation,
    })),
  };
}

function toPreview(dto: DeliveryPreviewDto): DeliveryPreview {
  return {
    inventoryEnabled: dto.inventory_enabled,
    requiresStockOutput: dto.requires_stock_output,
    allowNegativeStock: dto.allow_negative_stock,
    warehouses: dto.warehouses.map((w) => ({ id: w.id, name: w.name, isDefault: w.is_default })),
    warehouseId: dto.warehouse_id,
    lines: dto.lines.map((line) => ({
      productId: line.product.id,
      productName: line.product.name,
      quantity: line.quantity,
      unit: line.unit.abbreviation,
      available: line.available,
      projected: line.projected,
      insufficient: line.insufficient,
    })),
  };
}

function toReversal(dto: OrderReversalDto | null | undefined): OrderReversal | null {
  if (!dto) return null;
  return {
    movements: dto.movements.map((m) => ({
      id: m.id,
      productName: m.product.name,
      quantity: m.quantity,
      unit: m.unit.abbreviation,
      warehouseName: m.warehouse_name,
      reversedById: m.reversed_by_id,
      reversedByReference: m.reversed_by_reference,
    })),
    entries: dto.entries.map((e) => ({
      event: e.event,
      id: e.id,
      accountingDate: e.accounting_date,
      description: e.description,
      total: e.total,
      reversedById: e.reversed_by_id,
    })),
  };
}

function toReturnPreview(dto: ReturnPreviewDto): ReturnPreview {
  return {
    orderCode: dto.order_code,
    inventoryEnabled: dto.inventory_enabled,
    requiresRefundAcknowledgement: dto.requires_refund_acknowledgement,
    items: dto.items.map((i) => ({ productId: i.product.id, productName: i.product.name, quantity: i.quantity })),
    payments: dto.payments.map((p) => ({
      id: p.id,
      amount: p.amount,
      paymentMethod: p.payment_method,
      paymentDate: p.payment_date,
    })),
    stock: dto.stock
      ? {
          warehouseName: dto.stock.warehouse.name,
          lines: dto.stock.lines.map((l) => ({
            productId: l.product.id,
            productName: l.product.name,
            quantity: l.quantity,
            unit: l.unit.abbreviation,
          })),
        }
      : null,
    entries: dto.entries.map((e) => ({
      event: e.event,
      id: e.id,
      accountingDate: e.accounting_date,
      description: e.description,
      total: e.total,
    })),
  };
}

function toShortages(body: unknown): StockShortage[] {
  const lines = (body as { lines?: unknown } | null)?.lines;
  if (!Array.isArray(lines)) return [];
  return lines.map((raw) => {
    const line = raw as {
      product?: { id?: unknown; name?: unknown };
      unit?: { abbreviation?: unknown } | null;
      requested?: unknown;
      available?: unknown;
    };
    return {
      productId: String(line.product?.id ?? ''),
      productName: String(line.product?.name ?? ''),
      unit: typeof line.unit?.abbreviation === 'string' ? line.unit.abbreviation : null,
      requested: String(line.requested ?? ''),
      available: String(line.available ?? ''),
    };
  });
}

function toOrder(dto: OrderDto): Order {
  return {
    id: dto.id,
    code: dto.code,
    customer: dto.customer,
    salesChannel: dto.sales_channel,
    orderDate: dto.order_date,
    expectedDeliveryDate: dto.expected_delivery_date,
    deliveredDate: dto.delivered_date,
    notes: dto.notes,
    status: dto.status,
    paymentStatus: dto.payment_status,
    items: dto.items.map(toItem),
    subtotal: dto.subtotal,
    discount: dto.discount,
    total: dto.total,
    paidTotal: dto.paid_total,
    balance: dto.balance,
    payments: dto.payments.map(toPayment),
    cancellationReason: dto.cancellation_reason,
    cancelledAt: dto.cancelled_at,
    cancelledByName: dto.cancelled_by_name ?? '',
    returnedAt: dto.returned_at ?? null,
    returnedByName: dto.returned_by_name ?? '',
    returnReason: dto.return_reason ?? '',
    refundAcknowledged: dto.refund_acknowledged ?? false,
    reversal: toReversal(dto.reversal),
    editable: dto.editable,
    allowedTransitions: dto.allowed_transitions,
    canRegisterPayment: dto.can_register_payment,
    stockOutput: toStockOutput(dto.stock_output),
    warehouse: dto.warehouse ?? null,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function toSummary(dto: OrderSummaryDto): OrderSummary {
  return {
    id: dto.id,
    code: dto.code,
    customer: dto.customer,
    salesChannel: dto.sales_channel,
    orderDate: dto.order_date,
    expectedDeliveryDate: dto.expected_delivery_date,
    status: dto.status,
    paymentStatus: dto.payment_status,
    total: dto.total,
    paidTotal: dto.paid_total,
    balance: dto.balance,
  };
}

function toFieldErrors(body: unknown): FieldErrors {
  const errors: FieldErrors = {};
  if (body && typeof body === 'object') {
    for (const [name, value] of Object.entries(body as Record<string, unknown>)) {
      const field = FIELD_NAMES[name];
      if (field && Array.isArray(value)) {
        errors[field] = value.map((entry) => (typeof entry === 'string' ? entry : Object.values((entry ?? {}) as object).flat().join(' ')));
      }
    }
  }
  return errors;
}

function toPostingIssues(body: unknown): PostingIssue[] {
  const raw = (body as { issues?: unknown } | null)?.issues;
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((item): item is { code: string; subject: string; message: string } =>
      !!item && typeof item === 'object' && typeof (item as { message?: unknown }).message === 'string')
    .map((item) => ({ code: String(item.code ?? ''), subject: String(item.subject ?? ''), message: item.message }));
}

function ruleMessage(body: unknown): { code: string; detail: string } | null {
  if (body && typeof body === 'object') {
    const { code, detail } = body as { code?: unknown; detail?: unknown };
    if (typeof code === 'string' && typeof detail === 'string') {
      return { code, detail };
    }
  }
  return null;
}

function toApiError(err: HttpErrorResponse): OrderApiError {
  if (err.status === 0) {
    return new OrderApiError(NETWORK_ERROR_MESSAGE(), 0);
  }
  if (err.status === 400) {
    return new OrderApiError(VALIDATION_ERROR_MESSAGE(), 400, toFieldErrors(err.error));
  }
  if (err.status === 404) {
    const detail = (err.error as { detail?: unknown } | null)?.detail;
    return new OrderApiError(typeof detail === 'string' ? detail : NOT_FOUND_MESSAGE(), 404);
  }
  const rule = err.status === 409 ? ruleMessage(err.error) : null;
  if (rule) {
    const warehouse = (err.error as { warehouse?: { name?: unknown } }).warehouse;
    return new OrderRuleError(
      rule.detail,
      rule.code,
      rule.code === 'insufficient_stock' ? toShortages(err.error) : [],
      typeof warehouse?.name === 'string' ? warehouse.name : '',
      rule.code === 'posting_configuration_missing' ? toPostingIssues(err.error) : [],
    );
  }
  return new OrderApiError(GENERIC_ERROR_MESSAGE(), err.status);
}

function toBody(input: Partial<OrderInput>): Record<string, string | null> {
  const body: Record<string, string | null> = {};
  if (input.customerId !== undefined) body['customer_id'] = input.customerId;
  if (input.salesChannel !== undefined) body['sales_channel'] = input.salesChannel;
  if (input.orderDate !== undefined) body['order_date'] = input.orderDate;
  if (input.expectedDeliveryDate !== undefined) body['expected_delivery_date'] = input.expectedDeliveryDate;
  if (input.notes !== undefined) body['notes'] = input.notes;
  return body;
}

@Injectable({
  providedIn: 'root',
})
export class OrdersApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/orders/`;

  list(params: OrderListParams = {}): Observable<Page<OrderSummary>> {
    let httpParams = new HttpParams();
    if (params.status?.length) httpParams = httpParams.set('status', params.status.join(','));
    if (params.paymentStatus?.length) httpParams = httpParams.set('payment_status', params.paymentStatus.join(','));
    if (params.salesChannel) httpParams = httpParams.set('sales_channel', params.salesChannel);
    if (params.customerId) httpParams = httpParams.set('customer_id', params.customerId);
    if (params.dateField) httpParams = httpParams.set('date_field', params.dateField);
    if (params.dateFrom) httpParams = httpParams.set('date_from', params.dateFrom);
    if (params.dateTo) httpParams = httpParams.set('date_to', params.dateTo);
    if (params.hasBalance !== undefined) httpParams = httpParams.set('has_balance', String(params.hasBalance));
    if (params.ordering) httpParams = httpParams.set('ordering', params.ordering);
    if (params.page !== undefined) httpParams = httpParams.set('page', String(params.page));
    if (params.pageSize !== undefined) httpParams = httpParams.set('page_size', String(params.pageSize));
    return this.http.get<Page<OrderSummaryDto>>(this.baseUrl, { params: httpParams }).pipe(
      map((page): Page<OrderSummary> => ({ ...page, results: page.results.map(toSummary) })),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err))),
    );
  }

  get(id: string): Observable<Order> {
    return this.request(this.http.get<OrderDto>(`${this.baseUrl}${id}/`));
  }

  create(input: OrderInput): Observable<Order> {
    return this.request(this.http.post<OrderDto>(this.baseUrl, toBody(input)));
  }

  /** Crea el pedido completo (productos, descuento y almacén) ya en preparación, en una sola operación. */
  start(input: StartOrderInput): Observable<Order> {
    const body: Record<string, unknown> = {
      ...toBody(input),
      warehouse_id: input.warehouseId,
      discount: input.discount,
      items: input.items.map((item) => ({ product_id: item.productId, quantity: item.quantity })),
    };
    return this.request(this.http.post<OrderDto>(`${this.baseUrl}start/`, body));
  }

  update(id: string, input: Partial<OrderInput>): Observable<Order> {
    return this.request(this.http.patch<OrderDto>(`${this.baseUrl}${id}/`, toBody(input)));
  }

  addItem(orderId: string, productId: string, quantity: number): Observable<Order> {
    return this.request(
      this.http.post<OrderDto>(`${this.baseUrl}${orderId}/items/`, { product_id: productId, quantity }),
    );
  }

  changeItemQuantity(orderId: string, itemId: string, quantity: number): Observable<Order> {
    return this.request(this.http.patch<OrderDto>(`${this.baseUrl}${orderId}/items/${itemId}/`, { quantity }));
  }

  removeItem(orderId: string, itemId: string): Observable<Order> {
    return this.request(this.http.delete<OrderDto>(`${this.baseUrl}${orderId}/items/${itemId}/`));
  }

  applyDiscount(orderId: string, discount: string): Observable<Order> {
    return this.request(this.http.post<OrderDto>(`${this.baseUrl}${orderId}/discount/`, { discount }));
  }

  prepare(orderId: string): Observable<Order> {
    return this.request(this.http.post<OrderDto>(`${this.baseUrl}${orderId}/prepare/`, {}));
  }

  ready(orderId: string): Observable<Order> {
    return this.request(this.http.post<OrderDto>(`${this.baseUrl}${orderId}/ready/`, {}));
  }

  /** Qué pasaría al entregar (informativo): almacenes, existencias y saldo proyectado por producto. */
  deliveryPreview(orderId: string, warehouseId?: string): Observable<DeliveryPreview> {
    const params = warehouseId ? new HttpParams().set('warehouse_id', warehouseId) : new HttpParams();
    return this.http.get<DeliveryPreviewDto>(`${this.baseUrl}${orderId}/delivery-preview/`, { params }).pipe(
      map(toPreview),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err))),
    );
  }

  /** `warehouseId` solo se envía cuando el pedido tiene productos que controlan stock. */
  deliver(orderId: string, deliveredDate?: string, warehouseId?: string): Observable<Order> {
    const body: Record<string, string> = {};
    if (deliveredDate) body['delivered_date'] = deliveredDate;
    if (warehouseId) body['warehouse_id'] = warehouseId;
    return this.request(this.http.post<OrderDto>(`${this.baseUrl}${orderId}/deliver/`, body));
  }

  /** `refundAcknowledged`: el dinero ya cobrado se devolvió fuera de PocketBiz (obligatorio si hay cobros). */
  cancel(orderId: string, reason: string, refundAcknowledged = false): Observable<Order> {
    return this.request(
      this.http.post<OrderDto>(`${this.baseUrl}${orderId}/cancel/`, { reason, refund_acknowledged: refundAcknowledged }),
    );
  }

  /** Qué contrarrestaría la devolución total (informativo). */
  returnPreview(orderId: string): Observable<ReturnPreview> {
    return this.http.get<ReturnPreviewDto>(`${this.baseUrl}${orderId}/return-preview/`).pipe(
      map(toReturnPreview),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err))),
    );
  }

  /** Devolución total de un pedido entregado. */
  returnOrder(orderId: string, reason: string, refundAcknowledged = false): Observable<Order> {
    return this.request(
      this.http.post<OrderDto>(`${this.baseUrl}${orderId}/return/`, { reason, refund_acknowledged: refundAcknowledged }),
    );
  }

  registerPayment(orderId: string, input: PaymentInput): Observable<Order> {
    const body = {
      amount: input.amount,
      payment_method: input.paymentMethod,
      payment_date: input.paymentDate,
      reference: input.reference,
      idempotency_key: input.idempotencyKey,
    };
    return this.request(this.http.post<OrderDto>(`${this.baseUrl}${orderId}/payments/`, body));
  }

  private request(source: Observable<OrderDto>): Observable<Order> {
    return source.pipe(
      map(toOrder),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err))),
    );
  }
}
