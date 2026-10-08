import { Order, OrderDto, OrderItem, OrderSummary, Payment } from '../models/order';

export function makeItem(overrides: Partial<OrderItem> = {}): OrderItem {
  return {
    id: 'i-1',
    productId: 'p-1',
    productName: 'Pack cuñapé',
    unitPrice: '35.00',
    quantity: 2,
    subtotal: '70.00',
    ...overrides,
  };
}

export function makePayment(overrides: Partial<Payment> = {}): Payment {
  return {
    id: 'pay-1',
    amount: '20.00',
    paymentMethod: 'QR',
    paymentDate: '2026-10-02',
    reference: 'ref-1',
    createdAt: '2026-10-02T10:00:00Z',
    ...overrides,
  };
}

/** Pedido NEW editable con un ítem de 70.00 y sin pagos. */
export function makeOrder(overrides: Partial<Order> = {}): Order {
  return {
    id: 'o-1',
    code: 'P-1A2B3C4D',
    customer: { id: 'c-1', name: 'Ana Pérez' },
    salesChannel: 'WHATSAPP',
    orderDate: '2026-10-01',
    expectedDeliveryDate: '2026-10-05',
    deliveredDate: null,
    notes: 'Sin picante',
    status: 'NEW',
    paymentStatus: 'PENDING',
    items: [makeItem()],
    subtotal: '70.00',
    discount: '0.00',
    total: '70.00',
    paidTotal: '0.00',
    balance: '70.00',
    payments: [],
    cancellationReason: '',
    cancelledAt: null,
    editable: true,
    allowedTransitions: ['prepare', 'cancel'],
    canRegisterPayment: true,
    createdAt: '2026-10-01T10:00:00Z',
    updatedAt: '2026-10-01T11:00:00Z',
    ...overrides,
  };
}

export function makeSummary(overrides: Partial<OrderSummary> = {}): OrderSummary {
  return {
    id: 'o-1',
    code: 'P-1A2B3C4D',
    customer: { id: 'c-1', name: 'Ana Pérez' },
    salesChannel: 'WHATSAPP',
    orderDate: '2026-10-01',
    expectedDeliveryDate: '2026-10-05',
    status: 'NEW',
    paymentStatus: 'PENDING',
    total: '70.00',
    paidTotal: '0.00',
    balance: '70.00',
    ...overrides,
  };
}

/** Respuesta de la API (snake_case) equivalente a `makeOrder()`. */
export function makeOrderDto(overrides: Partial<OrderDto> = {}): OrderDto {
  return {
    id: 'o-1',
    code: 'P-1A2B3C4D',
    customer: { id: 'c-1', name: 'Ana Pérez' },
    sales_channel: 'WHATSAPP',
    order_date: '2026-10-01',
    expected_delivery_date: '2026-10-05',
    delivered_date: null,
    notes: 'Sin picante',
    status: 'NEW',
    payment_status: 'PENDING',
    items: [
      {
        id: 'i-1',
        product_id: 'p-1',
        product_name: 'Pack cuñapé',
        unit_price: '35.00',
        quantity: 2,
        subtotal: '70.00',
      },
    ],
    subtotal: '70.00',
    discount: '0.00',
    total: '70.00',
    paid_total: '0.00',
    balance: '70.00',
    payments: [],
    cancellation_reason: '',
    cancelled_at: null,
    editable: true,
    allowed_transitions: ['prepare', 'cancel'],
    can_register_payment: true,
    created_at: '2026-10-01T10:00:00Z',
    updated_at: '2026-10-01T11:00:00Z',
    ...overrides,
  };
}
