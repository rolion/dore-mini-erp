import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import {
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
  OrderSummary,
  OrderSummaryDto,
  Payment,
  PaymentDto,
  PaymentInput,
} from '../models/order';

export const NETWORK_ERROR_MESSAGE = 'No se pudo conectar con el servidor. Inténtalo de nuevo.';
export const NOT_FOUND_MESSAGE = 'Pedido no encontrado.';
export const GENERIC_ERROR_MESSAGE = 'Ocurrió un error inesperado. Inténtalo de nuevo.';
export const VALIDATION_ERROR_MESSAGE = 'Revisa los datos ingresados.';

const FIELD_NAMES: Record<string, OrderErrorField> = {
  customer_id: 'customerId',
  sales_channel: 'salesChannel',
  order_date: 'orderDate',
  expected_delivery_date: 'expectedDeliveryDate',
  notes: 'notes',
  product_id: 'productId',
  quantity: 'quantity',
  discount: 'discount',
  delivered_date: 'deliveredDate',
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
    editable: dto.editable,
    allowedTransitions: dto.allowed_transitions,
    canRegisterPayment: dto.can_register_payment,
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
        errors[field] = value.map(String);
      }
    }
  }
  return errors;
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
    return new OrderApiError(NETWORK_ERROR_MESSAGE, 0);
  }
  if (err.status === 400) {
    return new OrderApiError(VALIDATION_ERROR_MESSAGE, 400, toFieldErrors(err.error));
  }
  if (err.status === 404) {
    const detail = (err.error as { detail?: unknown } | null)?.detail;
    return new OrderApiError(typeof detail === 'string' ? detail : NOT_FOUND_MESSAGE, 404);
  }
  const rule = err.status === 409 ? ruleMessage(err.error) : null;
  if (rule) {
    return new OrderRuleError(rule.detail, rule.code);
  }
  return new OrderApiError(GENERIC_ERROR_MESSAGE, err.status);
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

  deliver(orderId: string, deliveredDate?: string): Observable<Order> {
    const body = deliveredDate ? { delivered_date: deliveredDate } : {};
    return this.request(this.http.post<OrderDto>(`${this.baseUrl}${orderId}/deliver/`, body));
  }

  cancel(orderId: string, reason: string): Observable<Order> {
    return this.request(this.http.post<OrderDto>(`${this.baseUrl}${orderId}/cancel/`, { reason }));
  }

  registerPayment(orderId: string, input: PaymentInput): Observable<Order> {
    const body = {
      amount: input.amount,
      payment_method: input.paymentMethod,
      payment_date: input.paymentDate,
      reference: input.reference,
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
