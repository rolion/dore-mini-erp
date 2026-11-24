import {
  DeliveryLine,
  DeliveryPreview,
  Order,
  OrderDto,
  OrderItem,
  OrderSummary,
  Payment,
  ReturnPreview,
} from '../models/order';

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
    cancelledByName: '',
    returnedAt: null,
    returnedByName: '',
    returnReason: '',
    refundAcknowledged: false,
    reversal: null,
    editable: true,
    allowedTransitions: ['prepare', 'cancel'],
    canRegisterPayment: true,
    stockOutput: null,
    warehouse: null,
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
    cancelled_by_name: '',
    returned_at: null,
    returned_by_name: '',
    return_reason: '',
    refund_acknowledged: false,
    reversal: null,
    editable: true,
    allowed_transitions: ['prepare', 'cancel'],
    can_register_payment: true,
    stock_output: null,
    warehouse: null,
    created_at: '2026-10-01T10:00:00Z',
    updated_at: '2026-10-01T11:00:00Z',
    ...overrides,
  };
}

export function makeDeliveryLine(overrides: Partial<DeliveryLine> = {}): DeliveryLine {
  return {
    productId: 'p-1',
    productName: 'Bolsas',
    quantity: '4.0000',
    unit: 'u',
    available: '5.0000',
    projected: '1.0000',
    insufficient: false,
    ...overrides,
  };
}

/** Vista previa con un almacén y una línea controlada, política de bloqueo. */
export function makePreview(overrides: Partial<DeliveryPreview> = {}): DeliveryPreview {
  return {
    inventoryEnabled: true,
    requiresStockOutput: true,
    allowNegativeStock: false,
    warehouses: [{ id: 'w-1', name: 'Central', isDefault: true }],
    warehouseId: 'w-1',
    lines: [makeDeliveryLine()],
    ...overrides,
  };
}

/** Pedido sin salida de inventario (Inventario deshabilitado o sin productos controlados). */
export const NO_STOCK_PREVIEW: DeliveryPreview = {
  inventoryEnabled: false,
  requiresStockOutput: false,
  allowNegativeStock: false,
  warehouses: [],
  warehouseId: null,
  lines: [],
};

/** Vista previa de devolución: una línea con salida de stock, dos asientos y sin cobros. */
export function makeReturnPreview(overrides: Partial<ReturnPreview> = {}): ReturnPreview {
  return {
    orderCode: 'P-1A2B3C4D',
    inventoryEnabled: true,
    requiresRefundAcknowledgement: false,
    items: [{ productId: 'p-1', productName: 'Bolsas', quantity: 2 }],
    payments: [],
    stock: { warehouseName: 'Central', lines: [{ productId: 'p-1', productName: 'Bolsas', quantity: '2.0000', unit: 'u' }] },
    entries: [
      { event: 'SALE_DELIVERY', id: 'e-1', accountingDate: '2026-10-03', description: 'Entrega', total: '70.00' },
      { event: 'INVENTORY_SALE_COST', id: 'e-2', accountingDate: '2026-10-03', description: 'Costo', total: '10.00' },
    ],
    ...overrides,
  };
}
